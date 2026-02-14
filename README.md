# mc-discord-bridge
A bridge between MeshCore and Discord.

## Configuration (config.ini) 🔧
Create `config.ini` from `config.ini.example` and set your own values.

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
python mc-discord-bridge.py
```

If `MSGBOT_TOKEN` is missing the program will exit with an error.

## Security note ⚠️
Keep `config.ini` out of version control because it may contain secrets (bot token). The repo provides `config.ini.example` as a template.

## Sending mesh messages to Discord: channel vs DM

- **To send a direct message (DM) to a Discord user**: send a mesh message that targets a DM in one of the supported formats. The bot recognizes:
	- `$name: message` — target by configured `name` followed by `:`
      e.g. `$meshuser: hello`.

	The `name` used for DM routing is looked up in the `[discord_dm_userids]` section of `config.ini` (keys are names, values are numeric Discord user IDs). Example:

	```ini
	[discord_dm_userids]
	alice = 123456789012345678
	bob = 987654321098765432
	```

	If a match is found, the bot will send the remainder of the mesh message (with `meshuser:` prefixed if present) as a DM to the corresponding Discord user.

- **To send to the configured Discord channel**: Post a message from mesh in the monitored MeshCore channel (configured via `CHNL_NAME_MESH`) and the bot will forward it to the Discord channel. Just make sure that the message doesn't start with the `$` character, or it will be interpreted as a DM


Notes and caveats:
- The bot only accepts DMs to users configured in `[discord_dm_userids]`.
- Names in the config are matched case-insensitively against the `name` token in the mesh message.
- Make sure the bot is invited to your server and has permission to send DMs (users can disable DMs from server members).
