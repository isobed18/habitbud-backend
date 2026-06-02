# chat/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, ChatMessage
from .serializers import ChatMessageSerializer
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.debug("ChatConsumer.connect() called")
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        # JWT Authentication - Try to get token from query string or headers
        token = None
        
        # Try query string first
        if self.scope.get('query_string'):
            query_string = self.scope['query_string'].decode()
            if 'token=' in query_string:
                token = query_string.split('token=')[1].split('&')[0]
        
        # Try headers if not in query string
        if not token:
            headers = dict(self.scope.get('headers', []))
            auth_header = headers.get(b'authorization', b'').decode()
            if auth_header.startswith('Bearer '):
                token = auth_header.split('Bearer ')[1]
        
        if not token:
            await self.close()
            return
        
        try:
            # Validate token
            UntypedToken(token)
            decoded_data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_data.get('user_id')
            
            if user_id:
                self.user = await database_sync_to_async(User.objects.get)(id=user_id)
                
                # Check if user is participant of conversation
                is_participant = await self.is_participant()
                if not is_participant:
                    await self.close()
                    return
                
                # Join room group
                logger.debug(f"Adding channel {self.channel_name} to group {self.room_group_name}")
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                
                # Join User Personal Group (for system notifications)
                self.user_group_name = f"user_{self.user.id}"
                logger.debug(f"Adding channel {self.channel_name} to user group {self.user_group_name}")
                await self.channel_layer.group_add(
                    self.user_group_name,
                    self.channel_name
                )
                
                logger.debug(f"WebSocket Accepted for User: {self.user.username}")
                await self.accept()
            else:
                logger.debug("No user_id in token")
                await self.close()
        except (InvalidToken, TokenError, User.DoesNotExist, Exception) as e:
            logger.error("WebSocket authentication error: %s", e)
            await self.close()

    async def disconnect(self, close_code):
        # Leave room group
        logger.debug(f"Disconnecting {self.channel_name} from {self.room_group_name}")
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Leave user group
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        logger.debug(f"WebSocket Received: {text_data}")
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'chat_message')
        
        if message_type == 'chat_message':
            content = text_data_json.get('content', '')
            
            # Save message to database (text only, proof images via REST API)
            message = await self.save_message(content=content)
            
            # Serialize message
            message_data = await self.serialize_message(message)
            
            # Send message to room group
            logger.debug(f"Sending to group {self.room_group_name}: {message_data.get('id')}")
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_data
                }
            )
        elif message_type == 'typing':
            # Broadcast typing indicator
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': str(self.user.id),
                    'username': self.user.username,
                    'is_typing': text_data_json.get('is_typing', False)
                }
            )

    async def chat_message(self, event):
        # Send message to WebSocket
        logger.debug(f"Sending to WebSocket Client: {event['message'].get('id')}")
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
        }))

    async def system_notification(self, event):
        # Send system notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'system_notification',
            'notification_type': event['notification_type'],
            'data': event['data']
        }))

    async def typing_indicator(self, event):
        # Send typing indicator to WebSocket
        # logger.debug(f"Sending typing indicator: {event['user_id']}")
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    @database_sync_to_async
    def is_participant(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return self.user in conversation.participants.all()
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            
            message = ChatMessage.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content,
                message_type='TEXT'
            )
            return message
        except Exception as e:
            logger.error("Error saving message: %s", e)
            return None

    @database_sync_to_async
    def serialize_message(self, message):
        if message:
            serializer = ChatMessageSerializer(message)
            return serializer.data
        return None

