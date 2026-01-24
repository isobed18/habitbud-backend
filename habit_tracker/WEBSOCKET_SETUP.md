# WebSocket Setup - Önemli!

## ⚠️ Sorun

Django development server (`python manage.py runserver`) **WebSocket'leri desteklemez**. WebSocket bağlantıları için **ASGI server** (Daphne) kullanmanız gerekiyor.

## ✅ Çözüm

### 1. Daphne ile Server'ı Başlat

Normal Django server yerine Daphne kullanın:

```bash
# Normal server (WebSocket çalışmaz)
python manage.py runserver

# Daphne ile (WebSocket çalışır)
daphne -b 0.0.0.0 -p 8000 habit_tracker.asgi:application
```

### 2. Redis'in Çalıştığından Emin Olun

WebSocket ve Channels için Redis gereklidir:

```bash
# Windows'ta Redis başlat (eğer yüklüyse)
redis-server

# Veya Docker ile
docker run -d -p 6379:6379 redis
```

### 3. Frontend'de Değişiklik Yapmanıza Gerek Yok

Frontend kodu doğru. Sadece backend'i Daphne ile çalıştırmanız yeterli.

## 🔧 Alternatif: Development için Basit Çözüm

Eğer Daphne kurulu değilse:

```bash
pip install daphne
```

Sonra:

```bash
daphne -b 0.0.0.0 -p 8000 habit_tracker.asgi:application
```

## 📝 Notlar

- **HTTP API'ler** normal Django server ile çalışır
- **WebSocket'ler** sadece Daphne ile çalışır
- Production'da da Daphne kullanılmalı (veya uWSGI + ASGI worker)

## 🚀 Production için

Production'da genellikle:
- Nginx (reverse proxy)
- Daphne (ASGI server)
- Redis (channel layers)

kullanılır.

