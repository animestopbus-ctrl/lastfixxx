import asyncio
import datetime
import sys
import os
from datetime import timezone, timedelta

from pyrogram import Client, filters, enums, __version__ as pyrogram_version
from pyrogram.types import Message

from config import API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL
from database.db import db
from logger import LOGGER

# ✅ Keep-alive server (For Render / Heroku)
try:
    from keep_alive import keep_alive
except ImportError:
    keep_alive = None

logger = LOGGER(__name__)

# ✅ Indian Standard Time
IST = timezone(timedelta(hours=5, minutes=30))

# ==============================================================================
# 🎨 CUSTOM BANNER (Printed in Terminal)
# ==============================================================================
LOGO = r"""


  ██████╗  ██╗  ██╗  █████╗  ███╗   ██╗ ██████╗   █████╗  ██╗      
  ██╔══██╗ ██║  ██║ ██╔══██╗ ████╗  ██║ ██╔══██╗ ██╔══██╗ ██║      
  ██║  ██║ ███████║ ███████║ ██╔██╗ ██║ ██████╔╝ ███████║ ██║      
  ██║  ██║ ██╔══██║ ██╔══██║ ██║╚██╗██║ ██╔═══╝  ██╔══██║ ██║      
  ██████╔╝ ██║  ██║ ██║  ██║ ██║ ╚████║ ██║      ██║  ██║ ███████



    𝙱𝙾𝚃 𝚆𝙾𝚁𝙺𝙸𝙽𝙶 𝙿𝚁𝙾𝙿𝙴𝚁𝙻𝚈....
"""

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Rexbots_Login_Bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="Rexbots"), 
            
            # ==================================================================
            # 🚀 SPEED & PERFORMANCE UPGRADES (Safe Radar)
            # ==================================================================
            workers=10,                        # Max concurrent tasks
            sleep_threshold=15,                 # Auto-sleep on FloodWait
            max_concurrent_transmissions=10,    # ⚡ Upload Speed Boost (10x)
            ipv6=False,                         # Disable IPv6 for stability
            in_memory=False,                    # Keep session on disk
            # ==================================================================
        )

    async def start(self):
        # 🔹 Print Banner to Terminal
        print(LOGO)
        
        # 🔹 Start Pyrogram
        await super().start()
        me = await self.get_me()

        # 🔹 Start keep-alive web server
        if keep_alive:
            try:
                keep_alive()
                logger.info("Keep-alive server started.")
            except Exception as e:
                logger.warning(f"Keep-alive failed to start: {e}")

        # 🔹 Log DB stats
        user_count = await db.total_users_count()
        logger.info(f"Connected to MongoDB Database: {db.db.name}")
        logger.info(f"Total Users in DB: {user_count}")

        # 🔹 Cache log channel
        try:
            await self.get_chat(LOG_CHANNEL)
            logger.info(f"Log Channel cached: {LOG_CHANNEL}")
        except Exception as e:
            logger.warning(f"Failed to cache log channel {LOG_CHANNEL}: {e}")

        # 🔹 Startup message
        now = datetime.datetime.now(IST)
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        startup_text = (
            f"<b><i>🤖 Bot Successfully Started ♻️</i></b>\n\n"
            f"<b>Bot:</b> @{me.username}\n"
            f"<b>Bot ID:</b> <code>{me.id}</code>\n\n"
            f"<b>📅 Date:</b> <code>{now.strftime('%d %B %Y')}</code>\n"
            f"<b>🕒 Time:</b> <code>{now.strftime('%I:%M %p')} IST</code>\n\n"
            f"<b>🐍 Python:</b> <code>{py_ver}</code>\n"
            f"<b>🔥 Pyrogram:</b> <code>{pyrogram_version}</code>\n"
            f"<b>🚀 Speed Mode:</b> <code>Enabled (10x)</code>\n\n"
            f"<b>👥 Total Users:</b> <code>{user_count}</code>\n\n"
            f"<b>Developed by @RexBots_Official</b>"
        )

        try:
            await self.send_message(
                LOG_CHANNEL,
                startup_text,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
            logger.info("Startup log sent successfully")
        except Exception as e:
            logger.error(f"Failed to send startup log: {e}")

        logger.info(f"Bot running as @{me.username}")

    async def stop(self, *args):
        try:
            me = await self.get_me()
            now = datetime.datetime.now(IST)

            stop_text = (
                f"<b><i>❌ Bot @{me.username} Stopped</i></b>\n\n"
                f"<b>📅 Date:</b> <code>{now.strftime('%d %B %Y')}</code>\n"
                f"<b>🕒 Time:</b> <code>{now.strftime('%I:%M %p')} IST</code>\n\n"
                f"<b>Developed by @RexBots_Official</b>"
            )

            await self.send_message(
                LOG_CHANNEL,
                stop_text,
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Failed to send stop log: {e}")

        await super().stop()
        logger.info("Bot stopped cleanly")


BotInstance = Bot()

# ========================================================
# ✅ NEW USER LOGGER
# Logs only on FIRST interaction
# ========================================================
@BotInstance.on_message(filters.private & filters.incoming, group=-1)
async def new_user_log(bot: Client, message: Message):
    user = message.from_user
    if not user:
        return

    # 1. Check if user exists
    if await db.is_user_exist(user.id):
        return

    # 2. Add user if not exists
    await db.add_user(user.id, user.first_name)

    # 3. Log the new user
    now = datetime.datetime.now(IST)
    username_text = f"@{user.username}" if user.username else "<i>None</i>"

    new_user_text = (
        f"<b><i>#NewUser 👤 Joined the Bot</i></b>\n\n"
        f"<b>Bot:</b> @{bot.me.username}\n\n"
        f"<b>User:</b> {user.mention(style='html')}\n"
        f"<b>Username:</b> {username_text}\n"
        f"<b>User ID:</b> <code>{user.id}</code>\n\n"
        f"<b>📅 Date:</b> <code>{now.strftime('%d %B %Y')}</code>\n"
        f"<b>🕒 Time:</b> <code>{now.strftime('%I:%M %p')} IST</code>\n\n"
        f"<b>Developed by @RexBots_Official</b>"
    )

    try:
        await bot.send_message(
            LOG_CHANNEL,
            new_user_text,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True
        )
        logger.info(f"New user logged: {user.id} - {user.first_name}")
    except Exception as e:
        logger.error(f"Failed to log new user {user.id}: {e}")


if __name__ == "__main__":
    BotInstance.run()
