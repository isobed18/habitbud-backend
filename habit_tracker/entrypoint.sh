#!/bin/bash
set -e

echo "🚀 Starting HabitBud setup..."

# Wait for Redis to be ready (simple check)
echo "⏳ Waiting for Redis..."
until python -c "import socket; s = socket.socket(); s.connect(('redis', 6379)); s.close()" 2>/dev/null; do
  echo "Waiting for Redis..."
  sleep 1
done
echo "✅ Redis is ready!"

# Run migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput

# Populate challenges (must be done before creating demo users)
echo "🎯 Populating challenge templates and items..."
python manage.py populate_challenges

# Seed predefined habit templates
echo "✅ Seeding habit templates..."
python manage.py seed_habit_templates

# Create demo users (optional - controlled by environment variable)
if [ "$CREATE_DEMO_USERS" = "true" ]; then
    echo "👥 Creating demo users..."
    python manage.py create_demo_users
    echo "✅ Demo users created!"
else
    echo "ℹ️  Skipping demo users creation (set CREATE_DEMO_USERS=true to enable)"
fi

# Collect static files (if needed)
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput || true

echo "✅ Setup complete! Starting server..."

# Execute the main command (from docker-compose or Dockerfile)
exec "$@"

