# Habit Tracker API Documentation

**Base URL:** `http://localhost:8000` (development)

**Authentication:** JWT Token (Bearer Token)
- Header: `Authorization: Bearer <access_token>`
- Token almak için: `/users/api/login/` veya `/users/api/register/`

---

## 📋 İçindekiler

1. [Authentication](#1-authentication)
2. [Habits](#2-habits)
3. [Friends](#3-friends)
4. [Chat & Conversations](#4-chat--conversations)
5. [Stories](#5-stories)
6. [Proof Submission & Verification](#6-proof-submission--verification)
7. [~~AI Coach & Assistant~~](#7-ai-coach--assistant) *(Shelved - returns 503)*
8. [Challenges & Rewards](#8-challenges--rewards)
9. [WebSocket](#9-websocket)
10. [Gamification Mechanics](#10-gamification-mechanics)
11. [User Search](#11-user-search)
12. [Notifications](#12-notifications)
13. [Achievements](#13-achievements)
14. [Health Check](#14-health-check)

---

## 1. Authentication

### 1.1 Register
**POST** `/users/api/register/`

**Authentication:** Not required

**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "password2": "string",
  "bio": "string (optional)"
}
```

**Response:** `201 Created`
```json
{
  "user": {
    "id": "uuid",
    "username": "string",
    "email": "string",
    "bio": "string"
  },
  "refresh": "string",
  "access": "string"
}
```

**Error Responses:**
- `400 Bad Request` - Validation errors
- `400 Bad Request` - Password fields didn't match

---

### 1.2 Login
**POST** `/users/api/login/`

**Authentication:** Not required

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:** `200 OK`
```json
{
  "user": {
    "id": "uuid",
    "username": "string",
    "email": "string",
    "bio": "string"
  },
  "refresh": "string",
  "access": "string"
}
```

**Error Responses:**
- `404 Not Found` - User not found
- `401 Unauthorized` - Invalid credentials

---

### 1.3 Logout
**POST** `/users/api/logout/`

**Authentication:** Required

**Request Body:**
```json
{
  "refresh": "string"
}
```

**Response:** `205 Reset Content`

**Error Responses:**
- `400 Bad Request` - Missing refresh token
- `400 Bad Request` - Invalid token

---

### 1.4 Token Refresh
**POST** `/users/api/token/refresh/`

**Authentication:** Not required (uses refresh token)

**Request Body:**
```json
{
  "refresh": "string"
}
```

**Response:** `200 OK`
```json
{
  "access": "string",
  "refresh": "string" (optional if rotation enabled)
}
```

---

### 1.5 Get Profile
**GET** `/users/api/profile/`

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "bio": "string",
  "xp": 0,
  "level": 1
}
```

---

### 1.6 Update Profile
**PUT** `/users/api/profile/`

**Authentication:** Required

**Request Body:** (all fields optional)
```json
{
  "email": "string",
  "bio": "string",
  "timezone": "Europe/Istanbul"
}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "bio": "string",
  "xp": 0,
  "level": 1
}
```

---

### 1.7 Leaderboard
**GET** `/users/api/leaderboard/`

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "username": "string",
    "email": "string",
    "bio": "string",
    "xp": 150,
    "level": 2
  },
  {
    "id": "uuid",
    "username": "string",
    "email": "string",
    "bio": "string",
    "xp": 50,
    "level": 1
  }
]
```

**Note:** Returns list of friends (including self) sorted by XP descending.

---

## 2. Habits

### 2.1 List Habits
**GET** `/habits/`

**Optional Query Params:**
- `date=YYYY-MM-DD`: Returns habit progress for a specific past date (History View). If omitted, returns active/today's progress.

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "name": "string",
    "habit_type": "count" | "time",
    "count": 0,
    "target_count": 10,
    "target_time": "HH:MM:SS" | null,
    "total_time": "HH:MM:SS" | null,
    "streak": 0,
    "verified_count": 0,        // New field
    "verification_streak": 0,    // New field
    "ai_streak": 0,             // New field (AI Specific Streak)
    "last_ai_verification_date": "YYYY-MM-DD" | null,
    "completed_count": 0,
    "last_completed_date": "YYYY-MM-DD" | null,
    "frequency": "daily" | "weekly" | "monthly" | "custom",
    "color": "green" | "yellow" | "purple" | "orange" | "pink" | "blue",
    "is_challenge_habit": false,    // New field
    "challenge": "uuid" | null      // New field (linked invitation/mission)
  }
]
```

**Note:** Response is cached for 5 minutes

---

### 2.2 Create Habit
**POST** `/habits/`

**Authentication:** Required

**Request Body:**
```json
{
  "name": "string",
  "habit_type": "count" | "time",
  "target_count": 10,  // Required if habit_type is "count"
  "target_time": "HH:MM:SS",  // Required if habit_type is "time"
  "frequency": "daily" | "weekly" | "monthly" | "custom",
  "color": "blue" // Optional, default: blue
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "name": "string",
  "habit_type": "count",
  "count": 0,
  "target_count": 10,
  "streak": 0,
  "completed_count": 0,
  "last_completed_date": null,
  "frequency": "daily"
}
```

**Error Responses:**
- `400 Bad Request` - Validation errors
- `400 Bad Request` - Target count/time required based on habit_type

---

### 2.3 Get Habit Detail
**GET** `/habits/{habit_id}/`

**Authentication:** Required

**Path Parameters:**
- `habit_id` (UUID) - Habit ID

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "name": "string",
  "habit_type": "count",
  "count": 5,
  "target_count": 10,
  "streak": 3,
  "completed_count": 15,
  "last_completed_date": "2024-01-15",
  "frequency": "daily"
}
```

**Error Responses:**
- `404 Not Found` - Habit not found or not owned by user

---

### 2.4 Update Habit
**PUT** `/habits/{habit_id}/`

**Authentication:** Required

**Path Parameters:**
- `habit_id` (UUID) - Habit ID

**Request Body:** (all fields optional, partial update)
```json
{
  "name": "string",
  "count": 5,
  "target_count": 10,
  "target_time": "HH:MM:SS",
  "frequency": "daily",
  "color": "purple"
}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "name": "string",
  "habit_type": "count",
  "count": 5,
  "target_count": 10,
  "streak": 3,  // Automatically recalculated
  "completed_count": 15,  // Automatically recalculated
  "last_completed_date": "2024-01-15",
  "frequency": "daily"
}
```

**Note:** After update, `update_and_recalculate()` is called automatically to update streak and completion stats.

**Error Responses:**
- `404 Not Found` - Habit not found or not owned by user
- `400 Bad Request` - Validation errors

---

### 2.5 Delete Habit
**DELETE** `/habits/{habit_id}/`

**Authentication:** Required

**Path Parameters:**
- `habit_id` (UUID) - Habit ID

**Response:** `204 No Content`

**Error Responses:**
- `404 Not Found` - Habit not found or not owned by user

---

### 2.6 Get Habit Statistics
**GET** `/habits/{habit_id}/stats/`

**Authentication:** Required

**Response:** `200 OK`
```json
{
    "current_streak": 5,
    "best_streak": 12,
    "total_completions": 45,
    "completion_rate": 85.5,
    "calendar": [
        {
            "date": "2024-01-01",
            "status": "partial",
            "count": 5
        },
        {
            "date": "2024-01-02",
            "status": "completed",
            "count": 10
        }
    ]
}
```

## 3. Friends

### 3.1 Send Friend Request
**POST** `/friends/request/`

**Authentication:** Required

**Request Body:**
```json
{
  "username": "string"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "from_user": {
    "id": "uuid",
    "username": "string",
    "bio": "string"
  },
  "to_user": {
    "id": "uuid",
    "username": "string",
    "bio": "string"
  },
  "status": "PENDING",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request` - Username is required
- `404 Not Found` - User not found
- `400 Bad Request` - Cannot send request to yourself
- `400 Bad Request` - Friend request already exists

---

### 3.2 List Pending Friend Requests
**GET** `/friends/requests/pending/`

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "from_user": {
      "id": "uuid",
      "username": "string",
      "bio": "string"
    },
    "to_user": {
      "id": "uuid",
      "username": "string",
      "bio": "string"
    },
    "status": "PENDING",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

**Note:** Returns only requests received by the current user with PENDING status

---

### 3.3 Respond to Friend Request
**POST** `/friends/requests/{request_id}/respond/`

**Authentication:** Required

**Path Parameters:**
- `request_id` (UUID) - Friend request ID

**Request Body:**
```json
{
  "action": "accept" | "decline"
}
```

**Response:** `200 OK`
```json
{
  "message": "Friend request accepted." | "Friend request declined."
}
```

**Error Responses:**
- `404 Not Found` - Friend request not found
- `400 Bad Request` - Request already responded to
- `400 Bad Request` - Invalid action

---

### 3.4 List Friends
**GET** `/friends/list/`

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "username": "string",
    "bio": "string"
  }
]
```

**Note:** Returns all users with ACCEPTED friendship status

---

### 3.5 List Friends (Alias)
**GET** `/users/friends/`

**Authentication:** Required

**Response:** `200 OK` (Same as 3.4)

---

## 4. Chat & Conversations

### 4.1 List Conversations
**GET** `/chat/conversations/`

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "participants": [
      {
        "id": "uuid",
        "username": "string",
        "email": "string",
        "bio": "string"
      }
    ],
    "last_message": {
      "id": "uuid",
      "sender": {...},
      "content": "string",
      "message_type": "TEXT" | "PROOF",
      "created_at": "2024-01-15T10:30:00Z"
    } | null,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### 4.2 Start Conversation
**POST** `/chat/conversations/start/`

**Authentication:** Required

**Request Body:**
```json
{
  "user_id": "uuid"
}
```

**Response:** `200 OK` (existing) or `201 Created` (new)
```json
{
  "id": "uuid",
  "participants": [
    {
      "id": "uuid",
      "username": "string",
      "email": "string",
      "bio": "string"
    }
  ],
  "last_message": null,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request` - user_id is required
- `400 Bad Request` - Cannot start conversation with yourself
- `403 Forbidden` - Can only start conversations with friends

---

### 4.3 List Messages
**GET** `/chat/conversations/{conversation_id}/messages/`

**Authentication:** Required

**Path Parameters:**
- `conversation_id` (UUID) - Conversation ID

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "sender": {
      "id": "uuid",
      "username": "string",
      "email": "string",
      "bio": "string"
    },
    "content": "string",
    "message_type": "TEXT" | "PROOF",
    "proof_image": "url" | null,
    "related_habit": "uuid" | null,
    "verification_status": "PENDING" | "VERIFIED" | "REJECTED" | null,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

**Error Responses:**
- `404 Not Found` - Conversation not found
- Returns empty array if user is not a participant

---

### 4.4 Create Message
**POST** `/chat/conversations/{conversation_id}/messages/create/`

**Authentication:** Required

**Path Parameters:**
- `conversation_id` (UUID) - Conversation ID

**Request Body:**
```json
{
  "content": "string",
  "related_habit_id": "uuid" (optional)
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "sender": {...},
  "content": "string",
  "message_type": "TEXT" | "PROOF",
  "proof_image": null,
  "related_habit": "uuid" | null,
  "verification_status": "PENDING" | null,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**
- `404 Not Found` - Conversation not found
- `403 Forbidden` - Not a participant of this conversation

---

---

## 7. AI Coach & Assistant

### 7.1 AI Habit Coach
**POST** `/chat/ai-coach/`

Get personalized coaching advice. The AI now analyzes your **last 7 days of history** and **recent chat context** for trend-aware guidance.

**Authentication:** Required

**Request Body:**
```json
{
  "habit_id": "uuid",
  "message": "I keep forgetting to drink water in the afternoon."
}
```

**Response:** `200 OK`
```json
{
  "advice": "Hydration is key! Since you have a 5-day streak but missed yesterday, try setting a phone alarm for 2 PM. You're doing great, Ishak!"
}
```

### 7.2 AI Agent
**POST** `/chat/ai-agent/`

Execute complex objectives using the IO.net Custom Agent (Workflows).

**Authentication:** Required

**Request Body:**
```json
{
  "objective": "Analyze my fitness goals and suggest a notification schedule.",
  "instructions": "Be very specific and actionable."
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": { ... agent output ... }
}
```

## 5. Stories

### 5.1 Create Story
**POST** `/chat/stories/create/`

**Authentication:** Required

**Request Body:** (multipart/form-data)
- `image`: File (required)
- `habit`: uuid (optional)
- `content`: string (optional)

**Response:** `201 Created`

### 5.2 Story Feed
**GET** `/chat/stories/feed/`

Returns active (non-expired) stories from friends and self.

**Response:** `200 OK` (list)
```json
[
  {
    "id": "uuid",
    "user": { ... },
    "image": "url",
    "content": "string",
    "likes_count": 5,
    "is_liked": true,
    "habit_details": {
      "id": "uuid",
      "name": "Running",
      "icon": "runner"
    },
    "created_at": "timestamp"
  }
]
```

### 5.3 Toggle Story Like
**POST** `/chat/stories/{story_id}/like/`

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "liked": true,
  "likes_count": 6
}
```

---

## 6. Proof Submission & Verification

### 6.1 Submit Proof (Social)
**POST** `/chat/proof/submit/`

**Authentication:** Required

**Request Body:** (multipart/form-data)
- `habit_id`: uuid (required)
- `proof_image`: File (required)
- `content`: string (optional)
- `conversation_id`: uuid (optional) - OR -
- `friend_id`: uuid (optional)

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "sender": {...},
  "content": "string",
  "message_type": "PROOF",
  "verification_status": "PENDING",
  "created_at": "timestamp"
}
```

### 6.2 Submit AI Proof (Solo)
**POST** `/chat/proof/ai/`

**Authentication:** Required

**Request Body:** (multipart/form-data)
- `habit_id`: uuid (required)
- `proof_image`: File (required)

**Response:** `200 OK`
```json
{
    "mode": "ai_verification",
    "ai_status": {
        "verified": true,
        "confidence": 0.95,
        "reason": "Image consistent with habit..."
    },
    "xp_awarded": 20
}
```



---

### 6.3 Verify/Reject Proof
**POST** `/chat/proof/{message_id}/verify/`

**Authentication:** Required

**Path Parameters:**
- `message_id` (UUID) - Chat message ID (must be PROOF type)

**Request Body:**
```json
{
  "action": "verify" | "reject"
}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "sender": {...},
  "content": "string",
  "message_type": "PROOF",
  "proof_image": "url",
  "related_habit": "uuid",
  "verification_status": "VERIFIED" | "REJECTED",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request` - Action must be 'verify' or 'reject'
- `404 Not Found` - Proof message not found
- `403 Forbidden` - Cannot verify your own proof
- `403 Forbidden` - Not a participant of this conversation

**Note:**
- Only friends can verify (not the sender)
- On verify: Updates habit's `verified_count` and `verification_streak`
- Broadcasts verification update via WebSocket

---

## 9. WebSocket

### 9.1 WebSocket Connection
**WebSocket** `ws://localhost:8000/ws/chat/{conversation_id}/?token={jwt_token}`

**Authentication:** JWT Token (query parameter or Authorization header)

**Path Parameters:**
- `conversation_id` (UUID) - Conversation ID

**Connection:**
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/chat/${conversationId}/?token=${accessToken}`);
```

**Alternative:** Use Authorization header
```javascript
// Note: Some WebSocket clients may not support custom headers
// Query parameter is more reliable
```

---

### 9.2 Send Message (via WebSocket)
**Message Format:**
```json
{
  "type": "chat_message",
  "content": "string"
}
```

**Response:**
```json
{
  "type": "message",
  "message": {
    "id": "uuid",
    "sender": {...},
    "content": "string",
    "message_type": "TEXT",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
const ws = new WebSocket(`ws://localhost:8000/ws/chat/${conversationId}/?token=${accessToken}`);
```

### 9.3 System Notifications (Global)
The backend pushes system-wide events (like Level Up) to the user via WebSocket.

**Event: Level Up**
```json
{
    "type": "system_notification",
    "notification_type": "level_up",
    "data": {
        "old_level": 1,
        "new_level": 2,
        "current_xp": 150
    }
}
```
**Usage:** Listen for `type: "system_notification"` to trigger UI effects.

---

## 10. Gamification Mechanics

### 10.1 XP & Leveling Curve
The system uses a **Non-Linear Progression** curve (Square Root).
- Formula: `Level = Sqrt(XP / 50) + 1`
- Early levels are fast, later levels require exponentially more XP.

### 10.2 Streak Multipliers (Snapchat Style)
Consistency is rewarded with bonus XP.
- **Components:** `Verified Habits` (AI/Social) and `Daily Completions`.
- **Base XP:** 10 per completion.
- **Multiplier:** `1.0x` + `0.05x` per day of streak (starting after Day 7).
- **Cap:** 3.0x Multiplier.

> **Example:** A 20-day streak earns `10 * 1.65 = 16 XP` per day (instead of 10).

---

### 9.4 Typing Indicator
**Send:**
```json
{
  "type": "typing",
  "is_typing": true | false
}
```

**Receive:**
```json
{
  "type": "typing",
  "user_id": "uuid",
  "username": "string",
  "is_typing": true | false
}
```

---

## 📝 Common Response Formats

### Error Response
```json
{
  "error": "Error message string"
}
```

### Validation Error Response
```json
{
  "field_name": ["Error message 1", "Error message 2"]
}
```

---

---

## 8. Challenges & Rewards

### 8.1 List Templates
**GET** `/challenges/templates/`

List all system-defined challenges (Solo/Duo) and their rewards.

**Response:** `200 OK` (list)
```json
[
  {
    "id": "uuid",
    "name": "30 Day Runner",
    "description": "...",
    "challenge_type": "SOLO" | "DUO",
    "duration_days": 30,
    "reward_xp": 500,
    "reward_points": 500,
    "reward_item": { "name": "Golden Shoes", "rarity": "epic", "image": "url" },
    "active_participants": 12
  }
]
```

### 8.2 Join Challenge
**POST** `/challenges/join/{template_id}/`

**Authentication:** Required

**Rules:** Joining a challenge **automatically creates a matched habit** for you.
- SOLO: Habit created immediately, status is ACTIVE. **Must NOT provide** `partner_id`.
- DUO: Status is PENDING. Habit is created only after partner accepts. **MUST provide** `partner_id`.
- **Mutual Auto-Accept:** If your partner recently invited YOU to the same challenge, joining will **immediately Activate** the challenge for both.

**Request Body:**
```json
{
  "partner_id": "uuid" // Required for DUO, Forbidden for SOLO
}
```



**Error Responses:**
- `400 Bad Request`: "Solo challenges cannot have a partner."
- `400 Bad Request`: "partner_id is required for Duo challenges."
- `400 Bad Request`: "You cannot be your own partner."

### 8.3 Withdraw Invitation
**POST** `/challenges/withdraw/{challenge_id}/`

**Authentication:** Required

Allows the creator to cancel a PENDING Duo invitation.

**Response:** `200 OK`

### 8.4 Accept/Reject Challenge
**POST** `/challenges/accept/{challenge_id}/`

**Request Body:**
```json
{
  "action": "accept" | "reject"
}
```
**Note:** On `accept`, matched habits are automatically created for BOTH the creator and the partner.

### 8.5 Active Challenges
**GET** `/challenges/active/`

Returns active and pending challenges. Use `waiting_for_me` to determine UI action.

**Response:** `200 OK`
```json
[
  {
     "id": "uuid",
     "template": { ... },
     "status": "ACTIVE" | "PENDING",
     "waiting_for_me": true, // TRUE if YOU need to accept/reject. FALSE if waiting for partner.
     "current_streak": 5,
     ...
  }
]
```

### 8.6 Duo Verification
**POST** `/challenges/{challenge_id}/verify/`

Used in Duo challenges. Friend A verifies that Friend B completed their habit today.
- **Rules:** Streak advances only if BOTH complete habits and BOTH verify each other.

### 8.7 Reward Scaling
Challenges now award **separate XP and Points**. 
- The `reward_points` from the template are added on top of the base points awarded per habit completion. 
- This ensures challenge completions are highly lucrative for the future market.

---

## 🔐 Authentication Flow

1. **Register** or **Login** to get `access` and `refresh` tokens
2. Include `access` token in Authorization header for all authenticated requests:
   ```
   Authorization: Bearer <access_token>
   ```
3. When `access` token expires, use `refresh` token to get new tokens (not implemented yet)
4. For WebSocket, pass token as query parameter: `?token=<access_token>`

---

## 📌 Notes

- All UUIDs are in standard UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- Date formats: `YYYY-MM-DD` for dates, `YYYY-MM-DDTHH:MM:SSZ` for datetimes
- Time formats: `HH:MM:SS` for duration fields
- Image URLs are relative paths that need to be prefixed with base URL and `/media/`
- All authenticated endpoints return `401 Unauthorized` if token is missing or invalid
- Habit streak and completion stats are automatically calculated on update

---

## 🚀 Quick Start Example

```javascript
// 1. Register
const registerResponse = await fetch('http://localhost:8000/users/api/register/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'testuser',
    email: 'test@example.com',
    password: 'password123',
    password2: 'password123'
  })
});
const { access, refresh } = await registerResponse.json();

// 2. Create Habit
const habitResponse = await fetch('http://localhost:8000/habits/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access}`
  },
  body: JSON.stringify({
    name: 'Daily Exercise',
    habit_type: 'count',
    target_count: 10,
    frequency: 'daily'
  })
});
const habit = await habitResponse.json();

// 3. Update Habit Count
await fetch(`http://localhost:8000/habits/${habit.id}/`, {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access}`
  },
  body: JSON.stringify({ count: 10 })
});

// 4. Connect WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/chat/${conversationId}/?token=${access}`);
```

---

## 11. User Search

### 11.1 Search Users
**GET** `/users/api/search/?q={query}`

**Authentication:** Required

**Query Parameters:**
- `q`: Search string (min 2 characters)

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "username": "string",
    "email": "string",
    "bio": "string",
    "xp": 0,
    "level": 1,
    "points": 0,
    "avatar": "url or null"
  }
]
```

---

## 12. Notifications

### 12.1 List Notifications
**GET** `/users/api/notifications/`

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "title": "string",
    "message": "string",
    "notification_type": "INFO|SUCCESS|WARNING|AI_AGENT",
    "is_read": false,
    "created_at": "datetime"
  }
]
```

### 12.2 Mark Notification as Read
**POST** `/users/api/notifications/{notification_id}/read/`

**Authentication:** Required

**Response:** `200 OK`
```json
{ "message": "Notification marked as read." }
```

### 12.3 Mark All Notifications as Read
**POST** `/users/api/notifications/read-all/`

**Authentication:** Required

**Response:** `200 OK`
```json
{ "message": "5 notifications marked as read." }
```

---

## 13. Achievements

### 13.1 List Achievements
**GET** `/achievements/`

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": "uuid",
    "name": "string",
    "description": "string",
    "icon": "url or null",
    "date_awarded": "datetime",
    "challenge": "uuid or null"
  }
]
```

---

## 14. Health Check

### 14.1 Health Check
**GET** `/api/health/`

**Authentication:** Not required

**Response:** `200 OK`
```json
{ "status": "ok", "service": "habitbud-backend" }
```

---

## 15. Friend Remove

### 15.1 Remove Friend
**DELETE** `/friends/remove/{friend_user_id}/`

**Authentication:** Required

**Response:** `200 OK`
```json
{ "message": "Friend removed." }
```

---

## Changelog

### v2.0.0 (2026-02-25) - Production Ready

**Breaking Changes:**
- AI proof verification is **shelved** (endpoints return `503 Service Unavailable`)
- Social proof no longer requires AI verification first
- `posts` app removed

**New Endpoints:**
- `GET /api/health/` - Health check
- `GET /users/api/search/?q=` - User search
- `GET /users/api/notifications/` - Notification list
- `POST /users/api/notifications/{id}/read/` - Mark notification read
- `POST /users/api/notifications/read-all/` - Mark all read
- `GET /achievements/` - Achievement list
- `DELETE /friends/remove/{id}/` - Remove friend

**Enhancements:**
- Friend list now includes `friendship_streak` and `last_interaction_date`
- Environment-based configuration (SECRET_KEY, DEBUG, DATABASE_URL)
- PostgreSQL support with SQLite fallback
- Redis/InMemory channel layer auto-detection
- Production security headers
- Logging configuration
