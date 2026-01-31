# Rexbots
# Don't Remove Credit
# Telegram Channel @RexBots_Official

import logging
import asyncio
import datetime
import time
import json
import os
from typing import Optional, List, Dict
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import (
    InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid
)
from database.db import db
from config import ADMINS
from logger import LOGGER

logger = LOGGER(__name__)

# ---------------------------------------------------
# Enhanced Broadcast Helper Function
# ---------------------------------------------------
async def broadcast_messages(client: Client, user_id: int, message: Message) -> tuple[bool, str]:
    """
    Attempts to forward a message to a user with robust error handling and retry logic.
    """
    try:
        await message.forward(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        logger.warning(f"FloodWait encountered for user {user_id}. Sleeping for {e.value} seconds.")
        await asyncio.sleep(e.value)
        return await broadcast_messages(client, user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logger.info(f"Deleted deactivated user {user_id}")
        return False, "Deleted"
    except UserIsBlocked:
        logger.info(f"User {user_id} has blocked the bot")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logger.info(f"Invalid peer for user {user_id}. Deleted from DB.")
        return False, "Error"
    except Exception as e:
        logger.error(f"Broadcast error for {user_id}: {e}")
        return False, "Error"

# ---------------------------------------------------
# /broadcast Command (Enhanced with Options and Progress Bar)
# ---------------------------------------------------
@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_command(bot: Client, message: Message) -> None:
    """
    Broadcasts the replied message to all/premium users with real-time progress updates.
    Usage: /broadcast [premium_only] (reply to message)
    """
    if not message.reply_to_message:
        return await message.reply_text(
            "**Usage:** Reply to a message with /broadcast [premium_only]",
            quote=True
        )
    
    premium_only = len(message.command) > 1 and message.command[1].lower() == "premium_only"
    b_msg = message.reply_to_message
    
    users_cursor = db.get_premium_users() if premium_only else db.get_all_users()
    target_group = "Premium Users" if premium_only else "All Users"
    
    sts = await message.reply_text(
        text=f"**__Preparing Broadcast to {target_group}...__**",
        quote=True
    )
    
    start_time = time.time()
    total_users = await db.total_premium_count() if premium_only else await db.total_users_count()
    done = 0
    blocked = 0
    deleted = 0
    failed = 0
    success = 0
    
    async for user in users_cursor:
        user_id = user.get('id')
        if not user_id or await db.is_banned(user_id):
            continue  # Skip invalid or banned users
        
        pti, sh = await broadcast_messages(bot, user_id, b_msg)
        if pti:
            success += 1
        else:
            if sh == "Blocked":
                blocked += 1
            elif sh == "Deleted":
                deleted += 1
            elif sh == "Error":
                failed += 1
        
        done += 1
        await asyncio.sleep(0.2)  # Gentle anti-flood delay
        
        # Real-time Progress Update with Bar
        if done % 10 == 0 or done == total_users:  # Update every 10 users
            percentage = (done / total_users * 100) if total_users > 0 else 0
            bar_length = 20
            filled = int(percentage / (100 / bar_length))
            bar = '█' * filled + ' ' * (bar_length - filled)
            
            await sts.edit_text(
                f"**__Broadcast In Progress to {target_group}:__**\n\n"
                f"**Progress: [{bar}] {percentage:.1f}%**\n"
                f"**👥 Total Users:** {total_users}\n"
                f"**💫 Completed:** {done} / {total_users}\n"
                f"**✅ Success:** {success}\n"
                f"**🚫 Blocked:** {blocked}\n"
                f"**🚮 Deleted:** {deleted}\n"
                f"**❌ Failed:** {failed}"
            )
    
    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.edit_text(
        f"**__Broadcast Completed to {target_group}:__**\n\n"
        f"**Progress: [██████████] 100%**\n"
        f"**⏰ Completed in:** {time_taken}\n\n"
        f"**👥 Total Users:** {total_users}\n"
        f"**💫 Completed:** {done} / {total_users}\n"
        f"**✅ Success:** {success}\n"
        f"**🚫 Blocked:** {blocked}\n"
        f"**🚮 Deleted:** {deleted}\n"
        f"**❌ Failed:** {failed}"
    )

# ---------------------------------------------------
# /users Command (Enhanced with Filters and Detailed Export)
# ---------------------------------------------------
@Client.on_message(filters.command("users") & filters.user(ADMINS))
async def users_count(bot: Client, message: Message) -> None:
    """
    Exports user data with optional filters (all, premium, banned) and detailed stats.
    Usage: /users [all|premium|banned] (default: all)
    """
    filter_type = message.command[1].lower() if len(message.command) > 1 else "all"
    
    if filter_type not in ["all", "premium", "banned"]:
        return await message.reply_text("**Invalid filter. Use: all, premium, or banned.**")
    
    msg = await message.reply_text(f"⏳ **__Gathering {filter_type.capitalize()} User Data...__**", quote=True)
    
    try:
        if filter_type == "all":
            users_cursor = db.get_all_users()
            total = await db.total_users_count()
        elif filter_type == "premium":
            users_cursor = db.get_premium_users()
            total = await db.total_premium_count()
        elif filter_type == "banned":
            users_cursor = db.get_banned_users()
            total = await db.total_banned_count()
        
        # Detailed Stats
        active_sessions = 0
        total_daily_usage = 0
        users_list: List[Dict] = []
        
        async for user in users_cursor:
            users_list.append({
                "id": user.get("id"),
                "name": user.get("name", "Unknown"),
                "username": user.get("username", "Unknown"),
                "is_premium": user.get("is_premium", False),
                "premium_expiry": str(user.get("premium_expiry", "N/A")),
                "is_banned": user.get("is_banned", False),
                "daily_usage": user.get("daily_usage", 0),
                "limit_reset_time": str(user.get("limit_reset_time", "N/A")),
                "session_active": bool(user.get("session")),
                "dump_chat": user.get("dump_chat", "None"),
                "delete_words_count": len(user.get("delete_words", [])),
                "replace_words_count": len(user.get("replace_words", {})),
                "caption_set": bool(user.get("caption")),
                "thumbnail_set": bool(user.get("thumbnail"))
            })
            active_sessions += 1 if user.get("session") else 0
            total_daily_usage += user.get("daily_usage", 0)
        
        avg_daily_usage = total_daily_usage / total if total > 0 else 0
        
        await msg.edit_text(
            f"🌀 **{filter_type.capitalize()} User Analytics Update** 🌀\n\n"
            f"👥 **Total Users:** {total}\n"
            f"🔑 **Active Sessions:** {active_sessions}\n"
            f"📊 **Total Daily Usage:** {total_daily_usage}\n"
            f"📈 **Avg Daily Usage/User:** {avg_daily_usage:.2f}\n"
            f"🧠 **Data Source:** MongoDB (async)"
        )
        
        if users_list:
            tmp_path = f"SaveRestricted_{filter_type}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(users_list, f, indent=4, ensure_ascii=False)
            
            caption = f"📄 **Exported {len(users_list)} {filter_type.capitalize()} Users**\n**Format:** JSON (Detailed)"
            await message.reply_document(
                document=tmp_path,
                caption=caption,
                quote=True
            )
            try:
                os.remove(tmp_path)
            except Exception as e:
                logger.error(f"[!] Failed to delete file {tmp_path}: {e}")
        else:
            await message.reply_text("**No users found for this filter.**", quote=True)
    except Exception as e:
        await msg.edit_text(f"**⚠️ Error Fetching User Data:**\n<code>{e}</code>")
        logger.error(f"[!] /users error: {e}")

# Credits
# Developer Telegram: @RexBots_Official
# Update channel: @RexBots_Official
# Rexbots
# Don't Remove Credit
# Telegram Channel @RexBots_Official
