#!/usr/bin/python
from email import message
import random
import re
import asyncio
import json
import os
import sys
import time
import urllib.request
import urllib.error
import logging
from meshcore import TCPConnection
from meshcore import MeshCore
from meshcore import EventType
import discord

# prefix mesh messsages DM_START_CHAR<user>:
# e.g. $Ferret:

DM_START_CHAR='$'

#set DEBUG_MESH=True to skip posting to discord
import configparser
cfg = configparser.ConfigParser()
# Preserve case of keys (by default ConfigParser converts to lowercase)
cfg.optionxform = str
# prefer a local config.ini; fallback to environment variables when keys are missing
cfg.read('config.ini')

def _cfg_get(section,key, default=None):
    if section in cfg and key in cfg[section]:
        return cfg[section][key]
    return default;

DEBUG_MESH = _cfg_get('meshcore','DEBUG_MESH', "False")

MESHCORE_HOSTNAME = _cfg_get('meshcore','MESHCORE_HOSTNAME', None)
PORT = int(_cfg_get('meshcore','PORT', "5000"))
CHNL_NAME_MESH = _cfg_get('meshcore','CHNL_NAME_MESH', "#discord")

WEBHOOK_URL = _cfg_get('discord','DISCORD_WEBHOOK_URL', None)
MSGBOT_TOKEN = _cfg_get('discord','MSGBOT_TOKEN', None)
_DISCORD_CHANNEL_ID = _cfg_get('discord','DISCORD_CHANNEL_ID', None)
if _DISCORD_CHANNEL_ID is not None:
    try:
        DISCORD_CHANNEL_ID = int(_DISCORD_CHANNEL_ID)
    except ValueError:
        print(f"WARNING: DISCORD_CHANNEL_ID is not a valid integer: {_DISCORD_CHANNEL_ID}")
        DISCORD_CHANNEL_ID = None
else:
    DISCORD_CHANNEL_ID = None

# Parse DISCORD_DM_USERIDS from [discord_dm_userids] section in config
# Maps userid (int) -> name (str) for DM filtering and display
DISCORD_DM_USERIDS = {}
if 'discord_dm_userids' in cfg:
    try:
        for name, userid_str in cfg['discord_dm_userids'].items():
            userid = int(userid_str.strip())
            DISCORD_DM_USERIDS[userid] = name
    except ValueError as e:
        print(f"WARNING: Invalid DISCORD_DM_USERIDS format in [discord_dm_userids] section (expected name=userid): {e}")

CHNL_IDX_MESH = None  # initialized by get_channels()


print(f"DEBUG_MESH={DEBUG_MESH}")    
print(f"MESHCORE_HOSTNAME={MESHCORE_HOSTNAME}",flush=True)    

# Set up logging to see discord.py debug info
logging.basicConfig(level=logging.DEBUG)
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.DEBUG)

#globals
con = None
mc = None
channels = []


def _post_discord_webhook(url: str, content: str) -> None:
    payload = {"content": content}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        # Some environments see Cloudflare 403 without an explicit UA
        "User-Agent": f"meshbot/1.0 (+https://example) Python/{sys.version_info[0]}.{sys.version_info[1]}"
    }
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        # Read to complete the request; response body is ignored
        _ = resp.read()


async def send_to_discord(webhook_url: str, content: str) -> None:
    if DEBUG_MESH == "True":
        return
    
    try:
        await asyncio.to_thread(_post_discord_webhook, webhook_url, content)
    except urllib.error.HTTPError as he:
        print(f"Discord webhook HTTP {he.code}: {he.reason}")
    except Exception as e:
        # Non-fatal: log and continue
        print(f"Discord webhook error: {e}")

async def help(message):
    await message.channel.send('$pub <msg>: send a msg in Public')
    await message.channel.send('$test <msg>: send a msg in #test')

async def get_channels():
    global channels
    global CHNL_IDX_MESH
    
    channel_idx = 0
    while True:
        res = await mc.commands.get_channel(channel_idx)
        if res.type == EventType.ERROR:
            break
        name = res.payload.get('channel_name')
        idx = res.payload.get('channel_idx')
        if name == CHNL_NAME_MESH:
            CHNL_IDX_MESH = idx
        if res.payload.get('channel_name') != '':
            channels.append(res.payload)
        channel_idx += 1

magic8_responses = ["It is certain.","It is decidedly so.","Without a doubt.","Yes definitely.","You may rely on it.","As I see it, yes.","Most likely.","Outlook good.","Yes.","Signs point to yes.","Reply hazy, try again.","Ask again later.","Better not tell you now.","Cannot predict now.","Concentrate and ask again.","Don't count on it.","My reply is no.","My sources say no.","Outlook not so good.","Very doubtful."]
def magic8():
    answer=magic8_responses[random.randint(0,len(magic8_responses)-1)]
    return answer

# do commands incoming from mesh    
async def do_mesh_commands(payload,channel_idx,channel_name,user,msg):
    doit = False
#    if channel_idx == CHNL_IDX_BOT:
#        doit = True
#    elif msg.lower().startswith(BOT_MESH_USER):
#        sidx = msg.find(']')
#        if sidx > 0:
#            msg = msg[sidx+1:]
#            print(msg)
#            doit = True

    if doit:
        resp = None
        msg = msg.lstrip()
        cmd = msg.lower()

        if cmd.startswith('test'):
            timestamp = payload.get('sender_timestamp')
#            snr = payload.get('SNR')
            hops = payload.get('path_len')
            text = payload.get('text')
            elapsed = round((time.time()-timestamp)*1000)
#            resp = f"ack {user}:{msg}|SNR:{snr}|hops:{hops}|{elapsed}ms"
            resp = f"ack {user}:{msg}|hops:{hops}|{elapsed}ms"
            print(resp)
        elif cmd.startswith('magic8'):
            msg = magic8()
            resp = f"[{user}]{msg}"

        if resp != None:
            #send to mesh
            res = await mc.commands.send_chan_msg(channel_idx,resp)
            print(res) # needs this or send flaky
            #send to discord
            if WEBHOOK_URL:
                webhook_message = f"[{channel_name}] {resp}"
                asyncio.create_task(send_to_discord(WEBHOOK_URL, webhook_message))        


async def mesh_listener () :
#    await meshconnect(con,mc)
    print("start")
    global con
    global mc
    con  = TCPConnection(MESHCORE_HOSTNAME, PORT)
    await con.connect()
    mc = MeshCore(con)
    await mc.connect()
    await get_channels()
    
    while True:
        result = await mc.commands.get_msg()
        if result.type == EventType.NO_MORE_MSGS:
            # No messages currently; wait briefly and continue listening
            await asyncio.sleep(0.1)
            continue
        elif result.type == EventType.ERROR:
            print(f"Error retrieving messages: {result.payload}")
            #            await meshconnect(mc)
            con  = TCPConnection(MESHCORE_HOSTNAME, PORT)
            await con.connect()
            mc = MeshCore(con)
            await mc.connect()
            continue
        # Extract and print channel name and text if available; otherwise fallback to raw result
        payload = getattr(result, 'payload', {}) or {}
#        print(payload)
        channel_idx = payload.get('channel_idx')
        text = payload.get('text')

        if channel_idx == CHNL_IDX_MESH and text is not None:
            # Strip "meshuser: " prefix if present
            meshuser = None
            if ': ' in text:
                parts = text.split(': ', 1)
                meshuser = parts[0].strip()
                remaining_text = parts[1]
            else:
                remaining_text = text
            
            if remaining_text.startswith(DM_START_CHAR):
                # Extract user $user: format and send DM
                target_name = None
                rest_of_text = None
                
                if remaining_text.startswith(DM_START_CHAR):
                    # Format: @user: message
                    colon_idx = remaining_text.find(':')
                    if colon_idx > 1:
                        target_name = remaining_text[1:colon_idx].strip()
                        rest_of_text = remaining_text[colon_idx+1:].strip()
                
                if target_name and rest_of_text is not None:
                    # Prefix meshuser to the message
                    if meshuser:
                        dm_content = f"[{meshuser}] {rest_of_text}"
                    else:
                        dm_content = rest_of_text
                    
                    # Find userid from name in DISCORD_DM_USERIDS (reverse lookup)
                    target_userid = None
                    for userid, name in DISCORD_DM_USERIDS.items():
                        if name.lower() == target_name.lower():
                            target_userid = userid
                            break
                    
                    if target_userid:
                        # Send DM to the user
                        try:
                            user = await client.fetch_user(target_userid)
                            await user.send(dm_content)
                            print(f"Sent DM to {target_name}: {dm_content}")
                        except Exception as e:
                            print(f"Failed to send DM to {target_name}: {e}")
                    else:
                        print(f"User {target_name} not found in DISCORD_DM_USERIDS")
            else:
                user = meshuser
                msg = remaining_text

                if user == None:
                    user = "meshcore"
                ansi_user = f"\x1b[37;44m{user}\x1b[0m"
                console_message = f"{ansi_user} {msg}"
                webhook_message = f"[{user}] {msg}"

                print(console_message)

                #post messages from CHNL_NAME_MESH to DISCORD_CHANNEL_ID
                if WEBHOOK_URL:
                    # Fire-and-forget to avoid blocking the receive loop
                    await send_to_discord(WEBHOOK_URL, webhook_message)
                
#            await do_mesh_commands(payload,channel_idx,channel_name,user,msg)


        else:
            print(result)


            
#testing
if DEBUG_MESH == "True":
    asyncio.run(mesh_listener())
    sys.exit()


# Enable the necessary intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.dm_messages = True  


# Create a client (bot) instance
client = discord.Client(intents=intents)

# Event triggered when the bot is ready
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    asyncio.create_task(mesh_listener())

# Event triggered when a message is sent in any channel
@client.event
async def on_message(message):
    # Ignore messages sent by the bot itself to prevent infinite loops
    if message.author.bot == True:
        return

# Check if the message is in a DM channel (only from allowed users)
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id in DISCORD_DM_USERIDS:
            dm_name = DISCORD_DM_USERIDS[message.author.id]
            print(f"New DM from {dm_name}: {message.content}")
            res = await mc.commands.send_chan_msg(CHNL_IDX_MESH,f"@[{dm_name}]{message.content.strip()}")
            print(res) # needs this or send flaky
        else:
            print(f"DM from {message.author.display_name} (ID: {message.author.id}) IGNORED (not in DISCORD_DM_USERIDS)")


    # Check if the message is from a specific channel (by ID)
    elif message.channel.id == DISCORD_CHANNEL_ID:
        print(f"received {message.author}: {message.content}")
        if CHNL_IDX_MESH is not None:
            res = await mc.commands.send_chan_msg(CHNL_IDX_MESH,f"[{message.author.display_name}]{message.content.strip()}")
            print(res) # needs this or send flaky
    else:
        print(f"Message from {message.author} in channel {message.channel.id} IGNORED (not DISCORD_CHANNEL_ID)")
#    elif message.content == "help":
#        asyncio.create_task(help())

# Run the bot with your token
# It's recommended to load your token from a config file or environment variable for security
if not MSGBOT_TOKEN:
    print("ERROR: MSGBOT_TOKEN not set in config.ini (section [bot]) or environment")
    sys.exit(1)

# Debug: show token status (masked)
token_status = f"***{MSGBOT_TOKEN[-10:]}" if len(MSGBOT_TOKEN) > 10 else "***"
print(f"MSGBOT_TOKEN loaded: {token_status}")
print(f"DISCORD_CHANNEL_ID: {DISCORD_CHANNEL_ID}")
print("Attempting to connect to Discord...")

try:
    client.run(MSGBOT_TOKEN)
except Exception as e:
    print(f"ERROR: Failed to connect to Discord: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
