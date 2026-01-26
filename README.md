# HabitBud - Social Habit Tracker with AI Verification

A next-generation habit tracking application that combines social accountability with AI-powered verification. Inspired by BeReal and Snapchat's authentic engagement model, HabitBud makes habit building a social, verified, and gamified experience.

## 🌟 What Makes HabitBud Different

Unlike traditional habit trackers, HabitBud focuses on **authenticity and social accountability**:

- **📸 Proof-Based Verification**: Submit photo proof of your habits (inspired by BeReal's authenticity)
- **🤖 AI-Powered Validation**: IO.net's Llama 4 Maverick model verifies your habit completion photos
- **👥 Social Accountability**: Friends verify each other's habits, building trust and motivation
- **📱 Stories & Engagement**: Share your progress through 24-hour stories (Snapchat-inspired)
- **🎮 Gamification**: XP, levels, streaks, and achievements keep you motivated
- **🏆 Challenges**: Solo and duo challenges with friends
- **🔔 Smart Reminders**: AI agent creates personalized daily reminders

## 🚀 Core Features

### 1. Dual Verification System
- **AI Verification**: Submit proof photos analyzed by IO.net's vision models
- **Social Verification**: Friends approve your habit completions
- **Hybrid Mode**: Combine both for maximum accountability

### 2. Social Features (BeReal/Snapchat Inspired)
- **24-Hour Stories**: Share habit achievements that expire after 24 hours
- **Friend System**: Add friends, view their progress, compete on leaderboards
- **Real-time Chat**: Message friends, share proof images, request verification
- **Streaks**: Maintain verification streaks with friends

### 3. AI Agent (Powered by IO.net)
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

## 🧠 IO.net Integration

HabitBud leverages **IO.net's decentralized GPU network** for AI capabilities:

### Primary Use Case: Proof Verification
```python
# When user submits a habit proof photo
result = IONetService.verify_habit_proof(
    image=proof_image,
    habit_name="Morning Run",
    username="john_doe"
)
# Returns: {"verified": true, "confidence": 0.95, "motivational_message": "..."}
```

**Model Used**: `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8`
- Vision-language model for image understanding
- Analyzes proof photos for authenticity
- Provides motivational feedback
- Prevents gaming the system with fake proofs

### Secondary Use Cases:
1. **AI Coach**: Personalized habit advice using `mistralai/Mistral-Nemo-Instruct-2407`
2. **AI Agent**: Complex workflow automation for habit creation and reminders

### Why IO.net?
- **Cost-Effective**: ~90% cheaper than traditional cloud AI
- **Decentralized**: No single point of failure
- **High Performance**: Access to latest models (Llama 4, Mistral)
- **Scalable**: Handles concurrent verification requests

## 📋 Prerequisites

- Python 3.10+
- SQLite3 (included with Python) - PostgreSQL is optional for production
- Redis 6+ (for WebSocket/Channels) - Optional for basic functionality
- IO.net API Key ([Get one here](https://io.net))

## 🐳 Quick Start with Docker (Recommended)

En hızlı kurulum yöntemi! Tek komutla tüm sistem hazır:

```bash
# Repository'yi klonlayın
git clone https://github.com/isobed18/habitbud-backend.git
cd habitbud-backend/habit_tracker

# İLK KURULUM: Cache olmadan build et ve başlat (önerilen)
docker-compose build --no-cache
docker-compose up -d

# VEYA tek komutla (cache olmadan):
docker-compose build --no-cache && docker-compose up -d
```

**İlk Kurulum Sonrası (Sonraki Kullanımlar):**
```bash
# Container'ları başlat (cache kullanır, daha hızlı)
docker-compose up -d

# Veya build ile birlikte (değişiklik varsa):
docker-compose up --build -d
```

Bu komutlar otomatik olarak:
- ✅ Redis container'ını başlatır
- ✅ Django uygulamasını build eder ve başlatır
- ✅ Database migrations'ları çalıştırır
- ✅ Challenge templates ve items'ları oluşturur
- ✅ Demo kullanıcıları oluşturur
- ✅ Server'ı `http://localhost:8000` adresinde başlatır

**Demo Kullanıcılar (Otomatik Oluşturulur):**

| Kullanıcı Adı | Şifre | Email | Açıklama |
|--------------|-------|-------|----------|
| `aslan_berk` | `password123` | berk@example.com | 45 günlük koşu serisi, disiplin odaklı |
| `zeynep_enerji` | `password123` | zeynep@example.com | 60 günlük su içme serisi, sağlık odaklı |
| `demir_disiplin` | `password123` | demir@example.com | 100 günlük kod yazma serisi, geliştirici |

**Docker Komutları:**
```bash
# Server'ı başlat (background)
docker-compose up -d

# Logları görüntüle
docker-compose logs -f web

# Tüm logları görüntüle
docker-compose logs -f

# Server'ı durdur
docker-compose down

# Server'ı durdur ve volume'ları sil (tamamen temizle)
docker-compose down -v

# Container durumunu kontrol et
docker-compose ps

# Demo kullanıcıları oluşturmadan başlatmak için:
# docker-compose.yml'de CREATE_DEMO_USERS=false yapın
```

**Önemli Notlar:**
- **İlk kurulum:** `--no-cache` kullanın, böylece tüm dependencies (pytz dahil) doğru şekilde yüklenir
- **Sonraki kullanımlar:** Cache kullanarak daha hızlı başlatabilirsiniz
- İlk build işlemi 1-2 dakika sürebilir (dependencies indirme)
- Sonraki başlatmalar çok daha hızlıdır (5-10 saniye)

---

## 🛠️ Manual Installation

### 1. Clone the Repository
```bash
git clone https://github.com/isobed18/habitbud-backend.git
cd habitbud-backend/habit_tracker
```

### 2. Create Virtual Environment

**ÖNEMLİ: `habit_tracker` dizininde olduğunuzdan emin olun**

```bash
# Eğer habit_tracker dizininde değilseniz:
cd habit_tracker

python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

**ÖNEMLİ: `habit_tracker` dizininde olduğunuzdan emin olun**

```bash
# Eğer habit_tracker dizininde değilseniz:
cd habit_tracker

pip install -r requirements.txt
```

### 4. Environment Configuration

**ÖNEMLİ: IPv4 Adresinizi Bulun**

Windows'ta IPv4 adresinizi bulmak için:
```bash
ipconfig
```
Çıktıda "IPv4 Address" satırını bulun (örnek: `192.168.1.9`). Bu adresi kullanacaksınız.

Create a `.env` file in the `habit_tracker` directory:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
# IPv4 adresinizi buraya ekleyin (ipconfig ile bulduğunuz adres)
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

**Not:** `.env` dosyası oluşturmanız zorunlu değildir. Proje varsayılan olarak SQLite kullanır ve çalışır.

### 5. Database Setup

**Not:** Proje varsayılan olarak SQLite kullanır. PostgreSQL kurulumu opsiyoneldir.

**ÖNEMLİ: `habit_tracker` dizininde olduğunuzdan emin olun**

```bash
# Eğer habit_tracker dizininde değilseniz:
cd habit_tracker

# Run migrations (SQLite otomatik oluşturulur)
python manage.py migrate

# Populate challenge templates (optional - ÖNCE bu çalıştırılmalı)
# Bu komut item'ları ve challenge template'lerini oluşturur
python manage.py populate_challenges

# Create demo users (optional - SONRA bu çalıştırılmalı)
# Demo kullanıcılar item'lara ihtiyaç duyar, bu yüzden önce populate_challenges çalıştırılmalı
python manage.py create_demo_users
```

**Demo Kullanıcı Bilgileri:**

| Kullanıcı Adı | Şifre | Email | Açıklama |
|--------------|-------|-------|----------|
| `aslan_berk` | `password123` | berk@example.com | 45 günlük koşu serisi, disiplin odaklı |
| `zeynep_enerji` | `password123` | zeynep@example.com | 60 günlük su içme serisi, sağlık odaklı |
| `demir_disiplin` | `password123` | demir@example.com | 100 günlük kod yazma serisi, geliştirici |

**PostgreSQL kullanmak isterseniz:**
```bash
# PostgreSQL database oluştur
createdb habitbud

# settings.py'de DATABASE_URL'i kullanacak şekilde yapılandırın
```

### 6. Create Superuser

**ÖNEMLİ: `habit_tracker` dizininde olduğunuzdan emin olun**

```bash
# Eğer habit_tracker dizininde değilseniz:
cd habit_tracker

python manage.py createsuperuser
```

### 7. Run Development Server

**ÖNEMLİ: IPv4 Adresinizi Kullanın**

Önce IPv4 adresinizi bulun:
```bash
# Windows
ipconfig

# Çıktıda "IPv4 Address" satırını bulun (örnek: 192.168.1.9)
```

**ÖNEMLİ: `habit_tracker` dizininde olduğunuzdan emin olun**

```bash
# Eğer habit_tracker dizininde değilseniz:
cd habit_tracker

# Start Redis (in separate terminal - Optional, sadece WebSocket için gerekli)
redis-server

# Start Django server
# 0.0.0.0 tüm ağ arayüzlerinde dinler, böylece telefonunuzdan da erişebilirsiniz
python manage.py runserver 0.0.0.0:8000
```

**Erişim URL'leri:**
- Yerel: `http://localhost:8000` veya `http://127.0.0.1:8000`
- Ağdan (telefon/başka bilgisayar): `http://192.168.1.9:8000` (IPv4 adresinizi kullanın)

### 8. Run WebSocket Server (Optional)
For real-time chat and notifications:
```bash
# WebSocket için Daphne kullanın (normal runserver WebSocket desteklemez)
daphne -b 0.0.0.0 -p 8001 habit_tracker.asgi:application
```

**Not:** WebSocket kullanmıyorsanız bu adımı atlayabilirsiniz. Normal HTTP API'ler için gerekli değildir.

## 🧪 Testing the AI Features

**Not:** `localhost` yerine IPv4 adresinizi kullanabilirsiniz (örnek: `192.168.1.9`)

### Test Proof Verification
```bash
# Using the API (localhost yerine IPv4 adresinizi de kullanabilirsiniz)
curl -X POST http://localhost:8000/chat/proof/ai/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "habit_id=HABIT_UUID" \
  -F "proof_image=@/path/to/photo.jpg"

# Veya IPv4 adresi ile:
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

# Veya IPv4 adresi ile:
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
- **Swagger UI**: `http://localhost:8000/api/docs/` veya `http://192.168.1.9:8000/api/docs/` (IPv4 adresinizi kullanın)
- **ReDoc**: `http://localhost:8000/api/redoc/` veya `http://192.168.1.9:8000/api/redoc/`
- **Markdown**: See `API_DOCUMENTATION.md`

**Not:** Telefon veya başka bir cihazdan erişmek için `localhost` yerine IPv4 adresinizi kullanın.

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
- **Database**: PostgreSQL (with UUID primary keys)
- **Real-time**: Django Channels + Redis
- **AI**: IO.net API (Llama 4, Mistral models)
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

- **IO.net**: For providing affordable, decentralized AI infrastructure
- **BeReal & Snapchat**: Inspiration for authentic social engagement
- **Django Community**: For the excellent framework and ecosystem

## 📧 Contact

For questions or collaboration: [Your Contact Info]

---

**Built with ❤️ using Django, IO.net, and a commitment to authentic habit building**
