# msgbot
A bridge between MeshCore and Discord.

## Configuration (config.ini) 🔧
The application reads configuration from `config.ini` (section `[bot]`). If a value is missing in `config.ini`, the program falls back to environment variables.

Create `config.ini` from `config.ini.example` and set your values (do **not** commit `config.ini` — it's ignored by `.gitignore`).

Example `config.ini` keys (in section `[bot]`):
- `DEBUG_MESH` — `True`/`False` (skip posting to Discord when `True`)
- `MESHCORE_HOSTNAME` — MeshCore hostname or IP
- `PORT` — port for MeshCore (default `5000`)
- `DISCORD_WEBHOOK_URL` — optional webhook to post messages
- `MSGBOT_TOKEN` — Discord bot token (required)
- `DISCORD_CHANNEL_ID` — numeric channel ID where bot listens

## Getting a Discord bot token 🔑
1. Go to the Discord Developer Portal: `https://discord.com/developers/applications`.
2. Click **New Application** → give it a name → **Create**.
3. In the application page choose **Bot** → **Add Bot** → **Yes, do it**.
4. Under **Privileged Gateway Intents** enable **Message Content Intent** (the bot sets `message_content` in code).
5. Click **Reset Token** (or **Copy**) to get the **Bot Token** — keep it secret. Paste it into `config.ini` as `MSGBOT_TOKEN`.
6. To invite the bot to your server: https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=3072&scope=bot
7. To find `DISCORD_CHANNEL_ID`: enable **Developer Mode** in your Discord client (User Settings → Advanced), right‑click the channel → **Copy ID**.

> Security tip: never commit your bot token. Use `config.ini` or environment variables.

## Usage ▶️
1. Copy `config.ini.example` → `config.ini` and edit values.
2. Start the bot as usual (it will read `config.ini` automatically):

```bash
python msgbot.py
```

If `MSGBOT_TOKEN` is missing the program will exit with an error.

## Security note ⚠️
Keep `config.ini` out of version control because it may contain secrets (bot token). The repo provides `config.ini.example` as a template.
