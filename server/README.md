# Running this PC as the HabitBud server

Turns this machine (192.168.1.8, RTX 3090) into an always-on backend host:
Daphne (HTTP + WebSockets) on port 8000, auto-started at boot, auto-restarted on
crash, reachable from the LAN — and optionally from the internet via a tunnel.

## 1. Install (once, as Administrator)

```powershell
powershell -ExecutionPolicy Bypass -File server\install_service.ps1
```

This opens TCP 8000 in the firewall, registers the **HabitBudServer** scheduled
task (boot, SYSTEM, hidden), and starts it. Logs: `server\logs\daphne-*.log`.

Manual foreground run (debugging): `powershell -File server\run_server.ps1`
Remove everything: `server\uninstall_service.ps1`

## 2. Make the LAN address stable

The app points at `http://192.168.1.8:8000/`. Reserve that IP so it never changes:
router admin → DHCP → **reserve 192.168.1.8 for this PC's MAC** (or set a static
IP in Windows network settings). Also disable Sleep: Settings → Power → "Never".

## 3. Internet access (optional, pick one)

| Option | Command | Notes |
|---|---|---|
| **Cloudflare Tunnel** (free, stable domain) | `winget install Cloudflare.cloudflared` then `cloudflared tunnel --url http://localhost:8000` | Quick mode gives a random `*.trycloudflare.com` URL; with a (free) Cloudflare-managed domain you get a permanent `api.yourdomain.com` + TLS. WebSockets supported. |
| **Tailscale** (free, private) | `winget install tailscale.tailscale` | Your devices join a private VPN; the phone reaches `http://<pc-tailscale-ip>:8000` from anywhere. No public exposure. Easiest + safest for personal/team use. |
| **Port forward** | router: WAN 8000 → 192.168.1.8:8000 | Public exposure — only with `DEBUG=False`, real `SECRET_KEY`, and ideally TLS in front (Caddy). Not recommended raw. |

For a public deployment use the production path instead (`DEPLOYMENT.md`,
Docker + TLS) — this folder is for the dev/LAN/always-on-PC scenario.

## 4. Production flags on this PC (recommended once stable)

Edit `habit_tracker\.env`:
```
DEBUG=False
SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(50))">
ALLOWED_HOSTS=192.168.1.8,localhost,127.0.0.1,<tunnel-domain>
SECURE_SSL_REDIRECT=False        # no TLS terminator on the LAN
```
Restart the task: `Stop-ScheduledTask HabitBudServer; Start-ScheduledTask HabitBudServer`.

## 5. Scheduled jobs

Reminders/pushes need the management commands on a schedule (Task Scheduler →
two basic tasks):
```
every 15 min:  habit_tracker\venv\Scripts\python.exe manage.py process_reminders
daily 18:00:   habit_tracker\venv\Scripts\python.exe manage.py send_check_reminders
```
(working directory: `habit_tracker\`)

## Health check

```
curl http://192.168.1.8:8000/api/health/   ->  {"status": "ok"}
```
