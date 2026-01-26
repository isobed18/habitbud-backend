# HabitBud - Social Habit Tracker with AI Verification

A next-generation habit tracking application that combines social accountability with AI-powered verification. Inspired by BeReal and Snapchat's authentic engagement model, HabitBud makes habit building a social, verified, and gamified experience.

**Frontend Repository**: [HabitBud Frontend](https://github.com/isobed18/habitbud-frontend)

## 🌟 What Makes HabitBud Different

Unlike traditional habit trackers, HabitBud focuses on **authenticity and social accountability**:

- **📸 Proof-Based Verification**: Submit photo proof of your habits (verified by IO Intelligence)
- **🤖 AI-Powered Validation**: IO Intelligence's Llama 4 Maverick model verifies your habit completion photos
- **👥 Social Accountability**: Friends verify each other's habits, building trust and motivation
- **📱 Stories & Engagement**: Share your progress through 24-hour stories (Snapchat-inspired)
- **🎮 Gamification**: XP, levels, streaks, and achievements keep you motivated
- **🏆 Challenges**: Solo and duo challenges with friends
- **🔔 Smart Reminders**: IO Intelligence agent creates personalized daily reminders

## 🚀 Core Features

### 1. Dual Verification System
- **AI Verification**: Submit proof photos analyzed by IO Intelligence vision models
- **Social Verification**: Friends approve your habit completions
- **Hybrid Mode**: Combine both for maximum accountability

### 2. Social Features (BeReal/Snapchat Inspired)
- **24-Hour Stories**: Share habit achievements that expire after 24 hours
- **Friend System**: Add friends, view their progress, compete on leaderboards
- **Real-time Chat**: Message friends, share proof images, request verification
- **Streaks**: Maintain verification streaks with friends

### 3. AI Coach & Agent (Powered by IO Intelligence)
- **Habit Suggestions**: AI recommends personalized habits based on your goals
- **Smart Reminders**: Schedule recurring notifications for habit practice
- **Coaching**: Get motivational advice and tips from the AI coach
- **Actionable Intelligence**: AI can directly create habits and reminders in your account

### 4. Gamification
- **XP System**: Earn experience points for completing habits
- **Levels**: Progress through levels as you build consistency
- **Streaks**: Daily, weekly, and monthly streak tracking
- **Achievements**: Unlock badges for milestones
- **Leaderboards**: Compete with friends

### 5. Challenges
- **Solo Challenges**: Personal 30/60/90-day challenges
- **Duo Challenges**: Partner with a friend for mutual accountability
- **Rewards**: Earn exclusive items and XP bonuses

## 🧠 Powered by IO Intelligence

HabitBud is built on **IO Intelligence (powered by IO.net)**, leveraging a decentralized GPU network to provide state-of-the-art AI capabilities that make authentic habit tracking possible.

### 🛡️ The AI Proof System (Core Differentiator)
Unlike other habit trackers that rely on simple button clicks, HabitBud enforces **Authenticity Through Proof**.
- **Mandatory Verification**: Users are required to submit photo proof to verify habit completion.
- **Vision-Language Model**: Powered by `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8`, our AI judge analyzes proof photos in real-time.
- **Incorruptible Judge**: The AI detects fake proofs, ensures the photo matches the habit description, and provides habit-specific motivational feedback.
- **XP Rewards**: Successful AI verification grants 20 XP and starts your AI verification streak.

```python
# The engine behind our mandatory verification
result = IONetService.verify_habit_proof(
    image=proof_image,
    habit_name="Morning Workspace Cleanup",
    username="john_doe"
)
# Returns: {"verified": true, "confidence": 0.98, "motivational_message": "Clean desk, clear mind! Great start, @john_doe!"}
```

### 🤖 Personal AI Coach & Agent
Beyond verification, IO Intelligence acts as a personal growth companion:
- **AI Coach**: Uses `mistralai/Mistral-Nemo-Instruct-2407` to provide context-aware coaching. It analyzes your last 7 days of performance and chat history to give personalized advice.
- **Unified AI Agent**: A custom agent capable of **Actionable Intelligence**. It doesn't just talk; it can directly:
    - Propose and **Create Habits** in your account.
    - **Schedule Reminders** based on your routine.
    - Send notifications and provide habit insights.

### Why IO Intelligence?
- **Next-Gen Models**: Access to high-performance models like Llama 4 and Mistral Nemo.
- **Scalable Performance**: Decentralized architecture ensures fast verification even during peak times.
- **Cost-Efficiency**: Leveraging decentralized GPUs allows us to provide premium AI features at a fraction of the cost.
- **True Authenticity**: Provides the technical foundation for a "Proof-of-Work" approach to personal habits.

---

## 📋 Prerequisites

- Python 3.10+
- SQLite3 (included with Python) - PostgreSQL is optional for production
- Redis 6+ (Required for **Real-time Chat**, **Stories**, and **Proof Verification** updates)
- IO Intelligence API Key ([Get one here](https://io.net))


## 🛠️ Manual Installation

### 1. Clone the Repository
```bash
git clone https://github.com/isobed18/habitbud-backend.git
cd habitbud-backend/habit_tracker
```

### 2. Create Virtual Environment

**IMPORTANT: Make sure you are in the `habit_tracker` directory**

```bash
# If you are not in the habit_tracker directory:
cd habit_tracker

python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

**IMPORTANT: Make sure you are in the `habit_tracker` directory**

```bash
# If you are not in the habit_tracker directory:
cd habit_tracker

pip install -r requirements.txt
```

### 4. Environment Configuration

**IMPORTANT: Find Your IPv4 Address**

To find your IPv4 address on Windows:
```bash
ipconfig
```
Find the "IPv4 Address" line in the output (e.g., `192.168.1.9`). You will use this address.

Create a `.env` file in the `habit_tracker` directory:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
# Add your IPv4 address here (the address you found with ipconfig)
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.9

# Database (SQLite kullanılıyorsa bu satırı atlayabilirsiniz)
# DATABASE_URL=postgresql://username:password@localhost:5432/habitbud

# Redis (for WebSockets - Optional)
REDIS_URL=redis://localhost:6379/0

# IO.net API
IONET_API_KEY=your-ionet-api-key
IONET_BASE_URL=https://api.intelligence.io.solutions/api/v1

# JWT Settings
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
```

**Note:** Creating a `.env` file is not mandatory. The project uses SQLite by default and will work.

### 5. Database Setup

**Note:** The project uses SQLite by default. PostgreSQL installation is optional.

**IMPORTANT: Make sure you are in the `habit_tracker` directory**

```bash
# If you are not in the habit_tracker directory:
cd habit_tracker

# Run migrations (SQLite is created automatically)
python manage.py migrate

# Populate challenge templates (optional - this should be run FIRST)
# This command creates items and challenge templates
python manage.py populate_challenges

# Create demo users (optional - this should be run AFTER)
# Demo users need items, so populate_challenges must be run first
python manage.py create_demo_users
```

**Demo User Information:**

| Username | Password | Email | Description |
|--------------|-------|-------|----------|
| `runner` | `password123` | runner@example.com | 45-day running streak, discipline focused |
| `drinker` | `password123` | drinker@example.com | 60-day water drinking streak, health focused |
| `coder` | `password123` | coder@example.com | 100-day coding streak, developer |

**If you want to use PostgreSQL:**
```bash
# Create PostgreSQL database
createdb habitbud

# Configure settings.py to use DATABASE_URL
```

### 6. Create Superuser

**IMPORTANT: Make sure you are in the `habit_tracker` directory**

```bash
# If you are not in the habit_tracker directory:
cd habit_tracker

python manage.py createsuperuser
```

### 7. Run Development Server

**IMPORTANT: Use Your IPv4 Address**

First, find your IPv4 address:
```bash
# Windows
ipconfig

# Find the "IPv4 Address" line in the output (e.g., 192.168.1.9)
```

**IMPORTANT: Make sure you are in the `habit_tracker` directory**

```bash
# If you are not in the habit_tracker directory:
cd habit_tracker

# Start Redis (REQUIRED for real-time features: Chat, Stories, and Proofs)
redis-server

# Start Django server
# 0.0.0.0 listens on all network interfaces, so you can also access it from your phone
python manage.py runserver 0.0.0.0:8000
```

**Access URLs:**
- Local: `http://localhost:8000` or `http://127.0.0.1:8000`
- From network (phone/another computer): `http://192.168.1.9:8000` (Use your IPv4 address)

### 8. Run WebSocket Server (Optional)
For real-time chat and notifications:
```bash
# Use Daphne for WebSocket (normal runserver doesn't support WebSocket)
daphne -b 0.0.0.0 -p 8001 habit_tracker.asgi:application
```

**Note:** Redis is essential for the core social experience (Real-time Chat, Stories, and Proof notifications). If you only want to use the basic HTTP habit tracking APIs without social interaction, you can skip this step.

## 🧪 Testing the AI Features

**Note:** You can use your IPv4 address instead of `localhost` (e.g., `192.168.1.9`)

### Test Proof Verification
```bash
# Using the API (You can also use your IPv4 address instead of localhost)
curl -X POST http://localhost:8000/chat/proof/ai/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "habit_id=HABIT_UUID" \
  -F "proof_image=@/path/to/photo.jpg"

# Or with IPv4 address:
curl -X POST http://192.168.1.9:8000/chat/proof/ai/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "habit_id=HABIT_UUID" \
  -F "proof_image=@/path/to/photo.jpg"
```

### Test AI Agent
```bash
curl -X POST http://localhost:8000/chat/ai-agent/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Create 3 habits for becoming a better developer",
    "instructions": "Make them actionable and specific"
  }'

# Or with IPv4 address:
curl -X POST http://192.168.1.9:8000/chat/ai-agent/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "objective": "Create 3 habits for becoming a better developer",
    "instructions": "Make them actionable and specific"
  }'
```

## 📱 API Documentation

Full API documentation is available at:
- **Swagger UI**: `http://localhost:8000/api/docs/` or `http://192.168.1.9:8000/api/docs/` (Use your IPv4 address)
- **ReDoc**: `http://localhost:8000/api/redoc/` or `http://192.168.1.9:8000/api/redoc/`
- **Markdown**: See `API_DOCUMENTATION.md`

**Note:** To access from a phone or another device, use your IPv4 address instead of `localhost`.

### Key Endpoints

#### Authentication
- `POST /users/api/register/` - User registration
- `POST /users/api/login/` - Login (returns JWT tokens)
- `POST /users/api/token/refresh/` - Refresh access token

#### Habits
- `GET /habits/` - List user's habits
- `POST /habits/` - Create new habit
- `PUT /habits/{id}/` - Update habit (increment count)
- `GET /habits/{id}/stats/` - Get detailed statistics

#### Social
- `POST /friends/send/` - Send friend request
- `GET /friends/` - List friends
- `GET /chat/stories/feed/` - View friends' stories
- `POST /chat/stories/create/` - Create a story

#### Verification
- `POST /chat/proof/ai/` - Submit proof for AI verification
- `POST /chat/proof/submit/` - Submit proof to friend
- `POST /chat/proof/{id}/verify/` - Verify friend's proof

#### AI Features
- `POST /chat/ai-agent/` - Interact with AI agent
- `POST /chat/ai-coach/` - Get habit coaching advice

#### Challenges
- `GET /challenges/templates/` - List available challenges
- `POST /challenges/join/{id}/` - Join a challenge
- `GET /challenges/active/` - View active challenges

## 🏗️ Architecture

### Tech Stack
- **Backend**: Django 4.2 + Django REST Framework
- **Frontend**: [HabitBud Frontend](https://github.com/isobed18/habitbud-frontend)
- **Database**: PostgreSQL (with UUID primary keys)
- **Real-time**: Django Channels + Redis
- **AI Engine**: IO Intelligence (Llama 4, Mistral models)
- **Authentication**: JWT (Simple JWT)
- **Image Processing**: Pillow

### Key Design Patterns
- **Service Layer**: Business logic separated from views (`services.py`)
- **Atomic Transactions**: Streak calculations use database transactions
- **Caching**: Redis for session management and WebSocket state
- **Lazy Evaluation**: Habit resets calculated on-demand

### Database Schema Highlights
- **Habit Completion Tracking**: Separate `HabitCompletion` table for accurate streak calculation
- **Social Proof**: `ChatMessage` model with proof verification workflow
- **Stories**: 24-hour expiring content with likes
- **Challenges**: Template-based system with solo/duo support

## 🔧 Configuration

### IO.net Model Selection
Edit `habit_tracker/services.py` to change AI models:

```python
class IONetService:
    def __init__(self):
        # Proof verification (vision model)
        self.model = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"
        
        # Coaching (text model)
        self.coach_model = "mistralai/Mistral-Nemo-Instruct-2407"
```

### Reminder Processing
Set up a cron job to process recurring reminders:

```bash
# Run every minute
* * * * * cd /path/to/habit_tracker && python manage.py process_reminders
```

Or use Celery Beat for production.

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Use production database (not SQLite)
- [ ] Set up Redis for production
- [ ] Configure HTTPS
- [ ] Set up media file storage (S3/CloudFlare R2)
- [ ] Configure CORS for frontend domain
- [ ] Set up monitoring (Sentry recommended)
- [ ] Configure backup strategy
- [ ] Set up Celery for background tasks

### Recommended Stack
- **Hosting**: Railway, Render, or AWS
- **Database**: Managed PostgreSQL (Supabase, Neon)
- **Redis**: Upstash or Redis Cloud
- **Media Storage**: CloudFlare R2 or AWS S3
- **WebSockets**: Separate Daphne instance

## 📊 Performance Considerations

- **Streak Calculation**: O(n) where n = days in streak (optimized with indexes)
- **AI Verification**: ~2-5 seconds per image (IO.net latency)
- **WebSocket Connections**: Redis pub/sub for horizontal scaling
- **Database Queries**: Optimized with `select_related()` and `prefetch_related()`

## 🤝 Contributing

This is a portfolio project, but suggestions are welcome! Please open an issue first to discuss proposed changes.

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- **IO Intelligence (powered by IO.net)**: For providing affordable, decentralized AI infrastructure
- **BeReal & Snapchat**: Inspiration for authentic social engagement
- **Django Community**: For the excellent framework and ecosystem

## 📧 Contact

For questions or collaboration: [ishakbediryorganci@gmail.com](mailto:ishakbediryorganci@gmail.com) or GitHub: [isobed18](https://github.com/isobed18)

---

**Built with ❤️ using Django, IO Intelligence, and a commitment to authentic habit building**
