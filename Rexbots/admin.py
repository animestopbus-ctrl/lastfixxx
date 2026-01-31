# Rexbots
# Don't Remove Credit
# Telegram Channel @RexBots_Official

import logging
from typing import Optional
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from database.db import db
from config import ADMINS, DB_URI

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("ban") & filters.user(ADMINS))
async def ban(client: Client, message: Message) -> None:
    """
    Bans a user from using the bot.
    Usage: /ban user_id [reason]
    """
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/ban user_id [reason]`")
    
    try:
        user_id = int(message.command[1])
        reason = " ".join(message.command[2:]) if len(message.command) > 2 else "No reason provided"
        
        if not await db.is_user_exist(user_id):
            return await message.reply_text(f"**User {user_id} does not exist in the database.**")
        
        if await db.is_banned(user_id):
            return await message.reply_text(f"**User {user_id} is already banned.**")
        
        await db.ban_user(user_id)
        logger.info(f"Admin {message.from_user.id} banned user {user_id} for: {reason}")
        await message.reply_text(f"**User {user_id} Banned Successfully 🚫**\n**Reason:** {reason}")
    except ValueError:
        await message.reply_text("**Invalid user_id. It must be an integer.**")
    except Exception as e:
        logger.error(f"Error banning user: {e}")
        await message.reply_text("Error banning user.")

@Client.on_message(filters.command("unban") & filters.user(ADMINS))
async def unban(client: Client, message: Message) -> None:
    """
    Unbans a user, allowing them to use the bot again.
    Usage: /unban user_id
    """
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/unban user_id`")
    
    try:
        user_id = int(message.command[1])
        if not await db.is_user_exist(user_id):
            return await message.reply_text(f"**User {user_id} does not exist in the database.**")
        
        if not await db.is_banned(user_id):
            return await message.reply_text(f"**User {user_id} is not banned.**")
        
        await db.unban_user(user_id)
        logger.info(f"Admin {message.from_user.id} unbanned user {user_id}")
        await message.reply_text(f"**User {user_id} Unbanned Successfully ✅**")
    except ValueError:
        await message.reply_text("**Invalid user_id. It must be an integer.**")
    except Exception as e:
        logger.error(f"Error unbanning user: {e}")
        await message.reply_text("Error unbanning user.")

# Rexbots
# Don't Remove Credit
# Telegram Channel @RexBots_Official

@Client.on_message(filters.command("set_dump") & filters.user(ADMINS))
async def set_dump(client: Client, message: Message) -> None:
    """
    Sets a dump chat for a user where files will be forwarded.
    Usage: /set_dump user_id chat_id
    """
    if len(message.command) < 3:
        return await message.reply_text("**Usage:** `/set_dump user_id chat_id`")
    
    try:
        user_id = int(message.command[1])
        chat_id = int(message.command[2])
        
        if not await db.is_user_exist(user_id):
            return await message.reply_text(f"**User {user_id} does not exist in the database.**")
        
        await db.set_dump_chat(user_id, chat_id)
        logger.info(f"Admin {message.from_user.id} set dump chat {chat_id} for user {user_id}")
        await message.reply_text(f"**Dump chat set for user {user_id} to {chat_id}.**")
    except ValueError:
        await message.reply_text("**Invalid user_id or chat_id. Both must be integers.**")
    except Exception as e:
        logger.error(f"Error setting dump chat: {e}")
        await message.reply_text("Error setting dump chat.")

@Client.on_message(filters.command("dblink") & filters.user(ADMINS))
async def dblink(client: Client, message: Message) -> None:
    """
    Retrieves the database URI for admin reference (masked for security).
    Usage: /dblink
    """
    masked_uri = DB_URI[:10] + "******" + DB_URI[-10:] if DB_URI else "Not set"
    await message.reply_text(f"**DB URI (Masked):** `{masked_uri}`\n\n**Note:** Keep this secure and do not share publicly.")

@Client.on_message(filters.command(["add_unsubscribe", "del_unsubscribe"]) & filters.user(ADMINS))
async def manage_force_subscribe(client: Client, message: Message) -> None:
    """
    Placeholder for managing force subscribe (unsubscribe) features.
    This will be implemented in future updates.
    """
    await message.reply_text("Force Subscribe management feature is coming soon. Stay tuned!")

# Rexbots
# Don't Remove Credit
# Telegram Channel @RexBots_Official

@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats(client: Client, message: Message) -> None:
    """
    Displays detailed bot statistics including totals, breakdowns, and averages.
    Usage: /stats [user_id] (optional for user-specific stats)
    """
    try:
        user_id: Optional[int] = int(message.command[1]) if len(message.command) > 1 else None
        
        if user_id:
            if not await db.is_user_exist(user_id):
                return await message.reply_text(f"**User {user_id} does not exist in the database.**")
            
            user_info = await db.get_user_info(user_id)
            if not user_info:
                return await message.reply_text("**No data available for this user.**")
            
            text = f"**User {user_id} Statistics 📊**\n\n" \
                   f"**Name:** {user_info.get('name', 'Unknown')}\n" \
                   f"**Premium:** {'Yes' if user_info.get('is_premium', False) else 'No'}\n" \
                   f"**Expiry:** {user_info.get('premium_expiry', 'N/A')}\n" \
                   f"**Banned:** {'Yes' if user_info.get('is_banned', False) else 'No'}\n" \
                   f"**Daily Usage:** {user_info.get('daily_usage', 0)}\n" \
                   f"**Limit Reset:** {user_info.get('limit_reset_time', 'N/A')}\n" \
                   f"**Session Active:** {'Yes' if user_info.get('session') else 'No'}\n" \
                   f"**Dump Chat:** {user_info.get('dump_chat', 'None')}\n" \
                   f"**Custom Caption:** {bool(user_info.get('caption', False))}\n" \
                   f"**Custom Thumbnail:** {bool(user_info.get('thumbnail', False))}"
        else:
            total_users = await db.total_users_count()
            premium_users = await db.total_premium_count()
            banned_users = await db.total_banned_count()
            
            # Enhanced: Calculate more stats
            active_sessions = await db.col.count_documents({'session': {'$ne': None}})
            total_daily_usage = sum(user.get('daily_usage', 0) async for user in db.get_all_users())
            avg_daily_usage = total_daily_usage / total_users if total_users > 0 else 0
            
            text = f"**Bot Global Statistics 📊**\n\n" \
                   f"**Total Users:** {total_users}\n" \
                   f"**Premium Users:** {premium_users} ({(premium_users / total_users * 100):.2f}%)\n" \
                   f"**Banned Users:** {banned_users} ({(banned_users / total_users * 100):.2f}%)\n" \
                   f"**Active Sessions:** {active_sessions}\n" \
                   f"**Total Daily Usage:** {total_daily_usage}\n" \
                   f"**Average Daily Usage per User:** {avg_daily_usage:.2f}"
        
        await message.reply_text(text)
    except ValueError:
        await message.reply_text("**Invalid user_id for detailed stats.**")
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        await message.reply_text("Error fetching statistics.")

@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast(client: Client, message: Message) -> None:
    """
    Broadcasts a replied message to all users or a subset.
    Usage: Reply to a message with /broadcast [premium_only] (optional flag)
    """
    if not message.reply_to_message:
        return await message.reply_text("**Usage:** Reply to a message with /broadcast [premium_only]")
    
    premium_only = len(message.command) > 1 and message.command[1].lower() == "premium_only"
    
    users_cursor = db.get_premium_users() if premium_only else db.get_all_users()
    success_count = 0
    fail_count = 0
    
    async for user in users_cursor:
        if await db.is_banned(user['id']):
            continue  # Skip banned users
        try:
            await message.reply_to_message.forward(user['id'])
            success_count += 1
            await asyncio.sleep(0.5)  # Anti-flood delay
        except Exception as e:
            fail_count += 1
            logger.warning(f"Failed to broadcast to user {user['id']}: {e}")
    
    target = "Premium Users" if premium_only else "All Users"
    await message.reply_text(f"**Broadcast Complete 📢 to {target}**\n\n**Successful:** {success_count}\n**Failed:** {fail_count}")

@Client.on_message(filters.command("add_premium") & filters.user(ADMINS))
async def add_premium(client: Client, message: Message) -> None:
    """
    Adds premium status to a user with an expiry date.
    Usage: /add_premium user_id expiry_date (YYYY-MM-DD)
    """
    if len(message.command) < 3:
        return await message.reply_text("**Usage:** `/add_premium user_id expiry_date` (YYYY-MM-DD)")
    
    try:
        user_id = int(message.command[1])
        expiry_date = datetime.strptime(message.command[2], "%Y-%m-%d")
        
        if not await db.is_user_exist(user_id):
            return await message.reply_text(f"**User {user_id} does not exist in the database.**")
        
        if await db.is_premium(user_id):
            return await message.reply_text(f"**User {user_id} is already premium.**")
        
        await db.add_premium(user_id, expiry_date)
        logger.info(f"Admin {message.from_user.id} added premium to user {user_id} until {expiry_date}")
        await message.reply_text(f"**Premium added for user {user_id} until {expiry_date} 💎**")
    except ValueError:
        await message.reply_text("**Invalid user_id or date format. Date must be YYYY-MM-DD.**")
    except Exception as e:
        logger.error(f"Error adding premium: {e}")
        await message.reply_text("Error adding premium.")

@Client.on_message(filters.command("remove_premium") & filters.user(ADMINS))
async def remove_premium(client: Client, message: Message) -> None:
    """
    Removes premium status from a user.
    Usage: /remove_premium user_id
    """
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/remove_premium user_id`")
    
    try:
        user_id = int(message.command[1])
        if not await db.is_user_exist(user_id):
            return await message.reply_text(f"**User {user_id} does not exist in the database.**")
        
        if not await db.is_premium(user_id):
            return await message.reply_text(f"**User {user_id} is not premium.**")
        
        await db.remove_premium(user_id)
        logger.info(f"Admin {message.from_user.id} removed premium from user {user_id}")
        await message.reply_text(f"**Premium removed for user {user_id} ❌**")
    except ValueError:
        await message.reply_text("**Invalid user_id. It must be an integer.**")
    except Exception as e:
        logger.error(f"Error removing premium: {e}")
        await message.reply_text("Error removing premium.")

@Client.on_message(filters.command("user_info") & filters.user(ADMINS))
async def user_info(client: Client, message: Message) -> None:
    """
    Retrieves detailed information about a specific user.
    Usage: /user_info user_id
    """
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/user_info user_id`")
    
    try:
        user_id = int(message.command[1])
        user_data = await db.get_user_info(user_id)
        if not user_data:
            return await message.reply_text(f"**User {user_id} not found.**")
        
        text = f"**User Info for {user_id} 🔍**\n\n" \
               f"**Name:** {user_data.get('name', 'Unknown')}\n" \
               f"**Premium:** {user_data.get('is_premium', False)}\n" \
               f"**Premium Expiry:** {user_data.get('premium_expiry', 'N/A')}\n" \
               f"**Banned:** {user_data.get('is_banned', False)}\n" \
               f"**Daily Usage:** {user_data.get('daily_usage', 0)}\n" \
               f"**Limit Reset Time:** {user_data.get('limit_reset_time', 'N/A')}\n" \
               f"**Session:** {'Active' if user_data.get('session') else 'Inactive'}\n" \
               f"**Dump Chat:** {user_data.get('dump_chat', 'None')}\n" \
               f"**Delete Words:** {len(user_data.get('delete_words', []))}\n" \
               f"**Replace Words:** {len(user_data.get('replace_words', {}))}\n" \
               f"**Caption Set:** {'Yes' if user_data.get('caption') else 'No'}\n" \
               f"**Thumbnail Set:** {'Yes' if user_data.get('thumbnail') else 'No'}"
        
        await message.reply_text(text)
    except ValueError:
        await message.reply_text("**Invalid user_id. It must be an integer.**")
    except Exception as e:
        logger.error(f"Error fetching user info: {e}")
        await message.reply_text("Error fetching user info.")

# Rexbots
# Don't Remove Credit
# Telegram Channel @RexBots_Official
