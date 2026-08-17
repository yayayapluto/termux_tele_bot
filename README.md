# Termux TeleBot

Telegram bot + Termux agent for remotely controlling an Android phone over a private Tailscale network.

## What this MVP does

- Telegram `/start` menu with inline keyboards.
- Discovers installed `termux-*` commands on the Android device.
- Groups common Termux:API commands into useful menus.
- Executes Termux:API commands through a small HTTP agent running in Termux.
- Supports `/run <command>` for custom shell commands.
- Restricts Telegram access by Telegram user ID.
- Authenticates bot → Termux agent requests with a shared token.
- Uses Tailscale for transport; the agent is intended to be reachable only through the Tailscale interface.
- Includes command timeout and output-size limits.

## Architecture

```text
Telegram
   |
   | Telegram Bot API
   v
Python Bot
   |
   | HTTP over Tailscale
   v
Termux Agent :8787
   |
   +--> termux-battery-status
   +--> termux-location
   +--> termux-camera-photo
   +--> termux-notification
   +--> termux-toast
   +--> ...
   |
   +--> custom shell command
```

The Termux:API project exposes Android functionality to command-line programs, and its package provides client scripts such as `termux-battery-status`. See:
- https://github.com/termux/termux-api
- https://github.com/termux/termux-api-package

## 1. Prerequisites

### Android / Termux

Install:

1. Termux
2. Termux:API
3. Tailscale

Important: keep Termux and Termux:API from compatible installation sources/signatures. The official Termux:API project currently documents F-Droid as an installation source.

Inside Termux:

```bash
pkg update
pkg install python termux-api
pip install -r agent/requirements.txt
```

You may also need:

```bash
termux-setup-storage
```

Grant Android permissions to Termux:API when a command asks for them.

### Bot machine

The bot can run on a PC, VPS, Raspberry Pi, another Termux environment, etc.

Install Python 3.11+:

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r bot/requirements.txt
```

## 2. Tailscale

Install Tailscale on both machines and sign them into the same tailnet.

On Android, find the Tailscale IP:

```bash
tailscale ip -4
```

It should look like:

```text
100.x.y.z
```

Test from the bot machine:

```bash
curl http://100.x.y.z:8787/health
```

Do NOT port-forward the agent to the public internet.

For extra security, use Tailscale ACLs/grants so only the bot machine can reach the Android agent.

## 3. Create the bot

Open Telegram and talk to BotFather.

Create a bot and copy the token.

Get your Telegram numeric user ID. You can use a bot such as `@userinfobot`, or temporarily add logging to the bot.

## 4. Configure the bot

Copy:

```text
bot/.env.example
```

to:

```text
bot/.env
```

Example:

```env
TELEGRAM_BOT_TOKEN=123456:ABCDEF
ALLOWED_USER_IDS=123456789
AGENT_URL=http://100.64.12.34:8787
AGENT_TOKEN=replace-with-a-long-random-secret
REQUEST_TIMEOUT=30
MAX_OUTPUT_CHARS=12000
```

For multiple Telegram users:

```env
ALLOWED_USER_IDS=123456789,987654321
```

Generate a strong agent token, for example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put the SAME token into the Termux agent `.env`.

## 5. Configure the Termux agent

Copy:

```text
agent/.env.example
```

to:

```text
agent/.env
```

Example:

```env
HOST=100.64.12.34
PORT=8787
AGENT_TOKEN=replace-with-a-long-random-secret
COMMAND_TIMEOUT=30
MAX_OUTPUT_CHARS=12000
```

`HOST` should be the Android device's Tailscale IPv4 address.

If your Tailscale setup makes binding to the specific address inconvenient, you can use:

```env
HOST=0.0.0.0
```

but then rely on Tailscale firewall/ACLs and the bearer token. Binding specifically to the Tailscale address is preferable when it works.

## 6. Start the agent

Inside Termux:

```bash
cd ~/termux-telebot
python -m agent.main
```

Expected:

```text
Termux agent listening on 100.x.y.z:8787
```

Health check:

```bash
curl http://100.x.y.z:8787/health
```

Expected JSON:

```json
{"ok":true,"service":"termux-agent"}
```

## 7. Start the Telegram bot

From the project root:

```bash
python -m bot.main
```

Open your Telegram bot and send:

```text
/start
```

You should get:

```text
📱 Termux Remote

[ 📱 Device ] [ 📡 Network ]
[ 📍 Location ] [ 📷 Camera ]
[ 🔊 Audio ] [ 💬 Notification ]
[ 🛠 Utilities ] [ 💻 Custom Command ]
```

## 8. Custom commands

Send:

```text
/run uptime
```

or:

```text
/run ls -lah
```

or:

```text
/run termux-battery-status
```

The command is executed on Android.

### Security note

Custom shell execution is intentionally powerful. Keep the Telegram allowlist enabled and never expose the agent publicly.

If you want a safer setup later, replace arbitrary `/run` with an allowlist of commands.

## 9. Termux:API discovery

The agent discovers available commands from:

```bash
$PREFIX/bin/termux-*
```

Therefore the keyboard reflects what is actually installed on the phone.

Useful commands may include:

```text
termux-battery-status
termux-camera-info
termux-camera-photo
termux-clipboard-get
termux-clipboard-set
termux-contact-list
termux-dialog
termux-fingerprint
termux-location
termux-media-player
termux-media-scan
termux-notification
termux-sensor
termux-share
termux-sms-list
termux-sms-send
termux-speech-to-text
termux-storage-get
termux-telephony-call
termux-telephony-cellinfo
termux-toast
termux-torch
termux-vibrate
termux-volume
termux-wifi-connectioninfo
termux-wifi-scaninfo
```

Exact availability depends on the installed Termux:API package/version and Android permissions.

## 10. Current MVP behavior

Commands with no required arguments can be executed directly from inline buttons.

Commands requiring interactive arguments are shown in the "Available APIs" area and can still be executed through:

```text
/run <command> <arguments>
```

Examples:

```text
/run termux-toast "hello from Telegram"
/run termux-vibrate -d 500
```

The MVP deliberately does not attempt to guess every command's argument schema. That is the next iteration.

## 11. Files

```text
termux-telebot/
├── README.md
├── .gitignore
├── bot/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── keyboards.py
│   ├── termux_client.py
│   ├── requirements.txt
│   └── .env.example
└── agent/
    ├── __init__.py
    ├── main.py
    ├── executor.py
    ├── requirements.txt
    └── .env.example
```

## 12. Troubleshooting

### `termux-battery-status: command not found`

Install the package:

```bash
pkg install termux-api
```

Also make sure the Termux:API Android app is installed.

### API command hangs

Check Android permissions and make sure the Termux:API app is installed from a compatible source.

Run the command directly in Termux first:

```bash
termux-battery-status
```

### Bot says agent is unreachable

Check:

```bash
tailscale ping <android-hostname-or-ip>
```

Then:

```bash
curl http://<TAILSCALE_IP>:8787/health
```

### Unauthorized

Make sure:

```env
AGENT_TOKEN=...
```

is exactly the same in both:

```text
bot/.env
agent/.env
```

### Telegram user is rejected

Make sure your numeric Telegram ID is present in:

```env
ALLOWED_USER_IDS=123456789
```

## 13. Running the agent in the background

For a first test, run it manually.

For long-running use, Android may kill background processes depending on battery optimization and Termux setup. Later, you can use Termux:Boot or another process supervisor suitable for your setup.

## 14. Roadmap

### v1
- [x] Telegram inline keyboard
- [x] Tailscale HTTP transport
- [x] Termux agent
- [x] Termux command discovery
- [x] Telegram user allowlist
- [x] Agent bearer token
- [x] `/run`
- [x] Basic output handling

### v2
- [ ] Automatic command categories
- [ ] Argument forms for commands
- [ ] Camera photo upload directly to Telegram
- [ ] Audio recording
- [ ] Location formatting
- [ ] Notification builder
- [ ] Volume controls
- [ ] Clipboard controls
- [ ] SMS form
- [ ] Permission/status dashboard

### v3
- [ ] File browser
- [ ] Download/upload
- [ ] Process manager
- [ ] Android screen capture
- [ ] Job queue
- [ ] Command history
- [ ] Audit log
- [ ] Multiple Android devices
- [ ] Per-device inline keyboards

## License

Use and modify this project as you like. Review the security implications before exposing shell execution to additional users.
