# HabitBud — Social Habit Tracker (Snapchat-style "Checks")

A simple, addictive habit tracker. You build habits, then send a **check** — a
quick photo proof, like a Snapchat snap — to your friends. They approve it, and
you earn XP and keep your streak alive. Duolingo-style streaks, haptics, instant
feedback, levels, and push notifications keep you coming back.

**Frontend Repository**: [HabitBud Frontend](https://github.com/isobed18/habitbud-frontend)

> No AI. Verification is 100% social — your friends are the judges.

## 🌟 Core Features

- **🐻 3D Animal Avatars & Dress-up System**: Personal 3D plushy animals (generated from 2D via Hunyuan3D-2) that breathing, bounce, tilt, and can be rotated with smooth inertia. Equipped with custom items (beanies, glasses, wands, books) attached to local anchors (`head`, `face`, `hand`, `back`, `neck`).
- **🛒 Gamification & Item Store**: Decoupled progression system dividing character Level/XP (lightning ⚡) from shop currency (diamonds 💎). Earn diamonds by levelling up and completing challenges, then spend them on Streak Freezes (❄️) or customizing your avatar.
- **❄️ Automated Streak Freezing**: Safeguards streaks when a check-in is missed. Automatically checks timezone-aware daily completions, uses a Streak Freeze from the user's inventory, and alerts the user.
- **📸 Checks (social proof)**: Snap a photo of your habit and send it to friends. They approve → you score. Features an **Undo (Geri Al) Slider** with a 4.5s countdown recall window to retract uploads.
- **🔥 Streaks & XP Multipliers**: Verified checks build habit + friendship streaks that multiply your XP. Milestones (5/7/14/30/60/100 days) trigger full-screen celebrations.
- **✅ Preset habit library**: One-tap habits (Su İç 💧, Yürüyüş 🚶, Spor 🏋️, Kitap 📖, Meditasyon 🧘, …) each with their own smart reminder copy.
- **🔔 Smart push notifications**: Habit-aware reminders ("Bugün su check'ini göndermeyi unutma 💧") and streak-at-risk nudges, delivered via Expo Push.
- **💬 Chat & group rooms**: 1:1 messaging plus group chat rooms, real-time over WebSockets. Sober Snapchat/Instagram style chat bubbles linked directly to profiles.
- **📱 24-hour Stories**: Share progress that expires after a day (Snapchat-inspired).
- **🏆 Challenges & Badges (Achievements)**: Solo/duo structured challenges (e.g. 30 Day Gym Rats, 7 Day Water Warrior) rewarding XP, diamonds, items, and permanent collectible badges.
- **✨ Premium Visual Effects & Haptics**: Full-screen Lottie confetti explosions, spring-animated floating reward chips, haptic clicks, and pulse animations for status changes.

## 🎮 Scoring (GamificationEngine)

| Action | Base XP | Multipliers |
|---|---|---|
| Send a check | +5 | — |
| Your check gets approved | +10 | × habit-streak × friendship-streak |
| You approve a friend's check | +3 | × friendship-streak |
| Self-complete (no check) | +5 | — |

- Habit streak multiplier: `1 + ln(1 + s/10)`
- Friendship streak multiplier: `1 + 0.5·ln(1 + fs/5)`
- Level: `floor(sqrt(xp/50)) + 1`

See [`users/gamification.py`](habit_tracker/users/gamification.py).

## 📋 Prerequisites

- Python 3.10+
- SQLite (default) or PostgreSQL (production)
- Redis 6+ (for real-time chat/stories; falls back to in-memory if absent)

## 🛠️ Installation

```bash
git clone https://github.com/isobed18/habitbud-backend.git
cd habitbud-backend/habit_tracker

python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Environment

Copy `.env.example` to `.env` and adjust. SQLite + in-memory channels work out
of the box, so a `.env` is optional for local dev. Key variables:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.9   # add your LAN IPv4 for phone access
# REDIS_HOST=127.0.0.1
# REDIS_PORT=6379
# EXPO_ACCESS_TOKEN=        # only if you enabled Expo enhanced push security
```

### Database & seed data

```bash
python manage.py migrate
python manage.py populate_challenges      # challenge templates + items
python manage.py seed_habit_templates     # preset habit catalog
python manage.py create_demo_users        # optional demo accounts

# Or do everything at once (flush + migrate + seed + demo):
python manage.py reset_db
```

**Demo users** (`password123`): `runner`, `drinker`, `coder`.

### Run

```bash
# ASGI server (HTTP + WebSockets) — listens on all interfaces for phone access
daphne -b 0.0.0.0 -p 8000 habit_tracker.asgi:application
# or, HTTP only:
python manage.py runserver 0.0.0.0:8000
```

Access from your phone at `http://<your-ipv4>:8000`. Set the same base URL in the
frontend's `services/axiosInstance.js`.

## 🔔 Smart reminders (cron)

Reminders and streak-at-risk nudges are sent by a management command — no Celery
needed. Schedule it hourly via cron / Windows Task Scheduler:

```bash
# every hour
0 * * * * cd /path/to/habit_tracker && /path/to/venv/bin/python manage.py send_check_reminders
```

It fires due per-habit reminders and, in the evening, warns users whose streaks
are about to break. Use `--dry-run` to preview without sending.

## 📡 Push notifications (Expo)

The backend stores each device's Expo push token (`POST /users/api/push-token/`)
and delivers notifications through the Expo Push API ([`users/push.py`](habit_tracker/users/push.py)).
All in-app notifications created via [`users/notifications.py`](habit_tracker/users/notifications.py)
are mirrored to push automatically. No FCM/APNs keys are required for Expo-managed apps.

## 📱 Key API Endpoints

**Auth**: `POST /users/api/{register,login,token/refresh}/`

**Habits**: `GET/POST /habits/`, `PUT /habits/{id}/`, `GET /habits/{id}/stats/`,
`GET /habits/templates/` (preset catalog)

**Checks**: `POST /chat/checks/submit/`, `POST /chat/checks/{id}/verify/`
(legacy `/chat/proof/...` aliases still work)

**Chat & rooms**: `GET /chat/conversations/`, `POST /chat/conversations/start/`,
`POST /chat/rooms/`, `POST|DELETE /chat/rooms/{id}/membership/`

**Stories**: `GET /chat/stories/feed/`, `POST /chat/stories/create/`

**Social**: `POST /friends/send/`, `GET /friends/`, `GET /users/api/search/?q=`

**Notifications/Push**: `GET /users/api/notifications/`, `POST /users/api/push-token/`

See [`API_DOCUMENTATION.md`](habit_tracker/API_DOCUMENTATION.md) for details.

## 🏗️ Architecture

- **Backend**: Django 5.1 + Django REST Framework
- **Real-time**: Django Channels + Redis (in-memory fallback)
- **Auth**: JWT (SimpleJWT)
- **Images**: Pillow
- **Push**: Expo Push API (via `requests`)
- **Database**: SQLite (dev) / PostgreSQL (prod), UUID primary keys

Design notes: service layer (`users/services.py`, `challange/services.py`),
atomic streak updates, lazy habit resets (computed on fetch, timezone-aware),
dynamic streak calculation from `HabitVerification` records.

## 🚀 Production checklist

- [ ] `DEBUG=False`, real `SECRET_KEY`, proper `ALLOWED_HOSTS`
- [ ] PostgreSQL + managed Redis
- [ ] HTTPS, CORS for the frontend domain
- [ ] Media storage (S3 / Cloudflare R2)
- [ ] Schedule `send_check_reminders` (cron / Task Scheduler)
- [ ] Run via Daphne (ASGI) behind a reverse proxy
- [ ] Monitoring (e.g. Sentry)

## 📄 License

MIT License — see LICENSE.

## 📧 Contact

[ishakbediryorganci@gmail.com](mailto:ishakbediryorganci@gmail.com) · GitHub: [isobed18](https://github.com/isobed18)

---

**Built with ❤️ using Django — authentic, social, no AI.**
