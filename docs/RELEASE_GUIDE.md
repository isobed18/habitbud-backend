# HabitBud — Uçtan Uca Yayın Rehberi (bu PC = server)

Bu rehber: backend'i bu PC'den internete açma, .env doldurma, iOS + Google Play
build/submit ve yayın sonrası işletme. Sıra önemli — yukarıdan aşağı uygula.

---

## 0. Satın alman / açman gerekenler (tek seferlik)

| Ne | Nereden | Ücret | Ne için |
|---|---|---|---|
| **Apple Developer** | developer.apple.com | $99/yıl | iOS build imzalama + App Store |
| **Google Play Console** | play.google.com/console | $25 tek sefer | Android yayın |
| **Alan adı** (örn. habitbud.app) | Cloudflare Registrar / Namecheap | ~$10/yıl | API adresi + e-posta |
| **E-posta servisi** | **Resend** (önerilen, 3k mail/ay ücretsiz) veya Brevo | $0 | doğrulama mailleri |
| Cloudflare hesabı | cloudflare.com | $0 | tünel + DNS + TLS |
| Expo hesabı (EAS) | expo.dev | $0 (ücretsiz kota yeter) | build servisi |

## 1. Bu PC'yi internete açık server yap

Backend Docker'lı ve test edildi (image build + container boot + health 200 ✅).
İki katman: **Windows servisi** (yerel) + **Cloudflare Tunnel** (internet + TLS).

```powershell
# 1) Yerel kalıcı servis (yönetici PowerShell)
powershell -ExecutionPolicy Bypass -File server\install_service.ps1
curl http://localhost:8000/api/health/        # {"status":"ok"} görmelisin

# 2) Cloudflare Tunnel (kalıcı, kendi domaininle)
winget install Cloudflare.cloudflared
cloudflared tunnel login                       # tarayıcıda domainini seç
cloudflared tunnel create habitbud
cloudflared tunnel route dns habitbud api.habitbud.app   # kendi domainin
# config: C:\Users\ishak\.cloudflared\config.yml
#   tunnel: habitbud
#   credentials-file: C:\Users\ishak\.cloudflared\<id>.json
#   ingress:
#     - hostname: api.habitbud.app
#       service: http://localhost:8000
#     - service: http_status:404
cloudflared service install                    # Windows servisi olarak kalıcı
```
Sonuç: `https://api.habitbud.app` → bu PC, TLS Cloudflare'de, WebSocket destekli.
Router'da port açmaya GEREK YOK (tünel dışarı doğru bağlanır).

> Alternatif (Docker yolu): `docker compose up -d --build` aynı işi Postgres +
> Redis ile yapar; tünel yine localhost:8000'i gösterir. Başlangıç için Windows
> servisi (SQLite) yeterli; kullanıcı artınca compose'a geç (DEPLOYMENT.md).

## 2. .env — doldurman gereken alanlar

`habit_tracker\.env` (şablon: `.env.example`):

```ini
# === ZORUNLU ===
SECRET_KEY=                # üret: python -c "import secrets;print(secrets.token_urlsafe(50))"
DEBUG=False
ALLOWED_HOSTS=api.habitbud.app,192.168.1.8,localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=https://api.habitbud.app
CSRF_TRUSTED_ORIGINS=https://api.habitbud.app
SECURE_SSL_REDIRECT=False  # TLS Cloudflare'de bitiyor — redirect döngüsünü önler
PUBLIC_API_URL=https://api.habitbud.app   # doğrulama maillerindeki link

# === E-POSTA (Resend örneği: resend.com -> API Keys -> SMTP) ===
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=       # Resend API key (re_...)
DEFAULT_FROM_EMAIL=no-reply@habitbud.app   # domainini Resend'de doğrula

# === SOSYAL GİRİŞ ===
GOOGLE_OAUTH_CLIENT_ID=    # console.cloud.google.com -> Credentials -> OAuth Client (iOS+Android+Web ayrı ayrı; Web client ID'yi buraya)
APPLE_BUNDLE_ID=com.isobed18.habitbud      # Apple dev hesabı sonrası

# === SATIN ALMA ===
APPLE_SHARED_SECRET=       # App Store Connect -> App -> App Information -> App-Specific Shared Secret
# GOOGLE_PLAY_SERVICE_ACCOUNT_JSON=C:\keys\play-sa.json   # Play Console servis hesabı (users/payments.py TODO)

# === AI DOĞRULAMA (bu PC'nin 3090'ı) ===
AI_VERIFY_PROVIDER=ollama
AI_VERIFY_URL=http://127.0.0.1:11434
AI_VERIFY_MODEL=qwen2.5vl:7b

# === OPSİYONEL ===
# REDIS_URL=redis://localhost:6379/0   # çoklu process / compose'da zorunlu
# THROTTLE_CHECKS=30/hour
```
Değiştirdikten sonra: `Stop-ScheduledTask HabitBudServer; Start-ScheduledTask HabitBudServer`

Ollama paralel (server/README.md): `OLLAMA_NUM_PARALLEL=4`, `OLLAMA_KEEP_ALIVE=24h`.

## 3. Frontend build — mağazalar

### Hazırlık (bir kez)
```powershell
cd C:\Users\ishak\habitbud-frontend
npm i -g eas-cli
eas login                                  # expo hesabın
```
`eas.json` → production profilindeki `API_URL`'i gerçek domainle değiştir:
`"API_URL": "https://api.habitbud.app/"`.
`app.json` kontrol: `version`, `ios.bundleIdentifier=com.isobed18.habitbud`,
`android.package=com.isobed18.habitbud` (mağazaya bir kez girince DEĞİŞTİRİLEMEZ).

### iOS (App Store)
```powershell
eas build --platform ios --profile production   # Apple hesabınla giriş ister; sertifikaları EAS yönetir
eas submit --platform ios --latest              # TestFlight'a yükler
```
App Store Connect'te: uygulama kaydı oluştur (aynı bundle id), ekran görüntüleri
(6.7" + 5.5"), gizlilik formu (foto/kamera kullanımı: habit kanıtı), yaş 4+.
Önce **TestFlight** ile kendine dağıt, sonra "Submit for Review".

### Android (Google Play)
```powershell
eas build --platform android --profile production   # .aab üretir; keystore'u EAS yönetir
eas submit --platform android --latest              # Play Console'a yükler (ilk seferde manuel yükleme isteyebilir)
```
Play Console'da: uygulama oluştur → İç test kanalına yükle → veri güvenliği
formu → üretime terfi. (İlk yayında Google incelemesi 1-7 gün.)

### Push bildirimleri
EAS build kullanınca Expo push token'ları otomatik çalışır (FCM/APNs
anahtarlarını `eas credentials` yönetir). Ek backend ayarı yok.

## 4. GitHub otomasyonu (eklendi)

Her iki repoda `.github/workflows/ci.yml`:
- **backend**: her push/PR'da — bağımlılık kurulumu, `manage.py check`,
  `makemigrations --check` (drift bekçisi), migrate + API smoke testi,
  Docker image build.
- **frontend**: bağımlılık kurulumu + tüm ekran/komponentlerin babel parse'ı +
  `expo config` doğrulaması.

Ek öneriler (hazır olunca): branch protection (CI yeşil olmadan merge yok),
`eas build` workflow'u (repo secret: `EXPO_TOKEN`), Dependabot.

## 5. Yayın sonrası işletme (bu PC)

| İş | Nasıl |
|---|---|
| Süreklilik | `HabitBudServer` task (boot'ta) + `cloudflared` servisi + PC uyku KAPALI |
| Loglar | `server\logs\daphne-*.log`; Cloudflare dash'te istek logları |
| Yedek | `db.sqlite3` + `media\` klasörünü günlük kopyala (Task Scheduler + robocopy → D:) |
| Hatırlatmalar | Task Scheduler: 15 dk'da bir `process_reminders`, 18:00 `send_check_reminders` (server/README.md) |
| Güncelleme | `git pull` → task'ı restart; migration varsa `manage.py migrate` |
| İzleme | UptimeRobot (ücretsiz) → `https://api.habitbud.app/api/health/` 5 dk'da bir |

## 6. KALAN EKSİKLER — senin aksiyonların

- [ ] Alan adı al + Cloudflare'e bağla → tüneli kur (Bölüm 1)
- [ ] `.env`'i Bölüm 2'deki gibi doldur (SECRET_KEY, email, Google client ID)
- [ ] Resend hesabı + domain doğrulama (maillerin spam'e düşmemesi için)
- [ ] Apple Developer ($99) + Google Play ($25) hesapları
- [ ] `eas.json` production API_URL'ini gerçek domainle değiştir
- [ ] iOS/Android production build + TestFlight/İç test ile cihazda doğrula
- [ ] Apple auth'u tamamlamak istersen: `users/auth_extras.py` AppleAuthView TODO
- [ ] Google Play satın alma doğrulaması: servis hesabı (`users/payments.py` TODO)
- [ ] Blender: kafa soketleri + item düzeltmeleri (docs/BLENDER_WORKFLOW.md)
- [ ] DB yedek görevini kur (yukarıdaki tablo)

Kod tarafında bilinen eksik yok: `check --deploy` 0 hata, migration drift 0,
smoke testler yeşil, Docker imajı konteynerde doğrulandı.
