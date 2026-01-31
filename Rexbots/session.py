import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid
)
from pyrogram import enums
from config import API_ID, API_HASH
from database.db import db
# ==========================================
# STATE MANAGEMENT
# Stores temporary login data
# {user_id: {"step": "WAITING_PHONE", "data": {...}}}
# ==========================================
LOGIN_STATE = {}
cancel_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("❌ Cancel")]],
    resize_keyboard=True
)
remove_keyboard = ReplyKeyboardRemove()
# Progress indicators using emojis for a colorful, visual feel
PROGRESS_STEPS = {
    "WAITING_PHONE": "🟢 Phone Number → 🔵 Code → 🔵 Password",
    "WAITING_CODE": "✅ Phone Number → 🟢 Code → 🔵 Password",
    "WAITING_PASSWORD": "✅ Phone Number → ✅ Code → 🟢 Password"
}
# Emoji-based loading animation frames
LOADING_FRAMES = [
    "🔄 Connecting •••",
    "🔄 Connecting ••○",
    "🔄 Connecting •○○",
    "🔄 Connecting ○○○",
    "🔄 Connecting ○○•",
    "🔄 Connecting ○••",
    "🔄 Connecting •••"
]
async def animate_loading(message: Message, duration: int = 5):
    """Animate a loading message for a few seconds."""
    for _ in range(duration):
        for frame in LOADING_FRAMES:
            try:
                await message.edit_text(f"<b>{frame}</b>", parse_mode=enums.ParseMode.HTML)
                await asyncio.sleep(0.5)
            except:
                return
# ---------------------------------------------------
# /login - Start Login Process
# ---------------------------------------------------
@Client.on_message(filters.private & filters.command("login"))
async def login_start(client: Client, message: Message):
    user_id = message.from_user.id
   
    # Check if already logged in
    user_data = await db.get_session(user_id)
    if user_data:
        return await message.reply(
            "<b>✅ You're already logged in! 🎉</b>\n\n"
            "To switch accounts, first use /logout.",
            parse_mode=enums.ParseMode.HTML
        )
    # Initialize State
    LOGIN_STATE[user_id] = {"step": "WAITING_PHONE", "data": {}}
   
    progress = PROGRESS_STEPS["WAITING_PHONE"]
    await message.reply(
        f"<b>👋 Hey! Let's log you in smoothly 🌟</b>\n\n"
        f"<i>Progress: {progress}</i>\n\n"
        "📞 Please send your <b>Telegram Phone Number</b> with country code.\n\n"
        "<blockquote>Example: +919876543210</blockquote>\n\n"
        "<i>💡 Your number is used only for verification and is kept secure. 🔒</i>\n\n"
        "❌ Tap the <b>Cancel</b> button or send /cancel to stop.",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=cancel_keyboard
    )
# ---------------------------------------------------
# /logout - Remove Session
# ---------------------------------------------------
@Client.on_message(filters.private & filters.command("logout"))
async def logout(client: Client, message: Message):
    user_id = message.from_user.id
   
    # Remove from state if exists
    if user_id in LOGIN_STATE:
        del LOGIN_STATE[user_id]
    # Remove from Database
    await db.set_session(user_id, session=None)
    await message.reply(
        "<b>🚪 Logout Successful! 👋</b>\n\n"
        "<i>Your session has been cleared. You can log in again anytime! 🔄</i>",
        parse_mode=enums.ParseMode.HTML
    )
# ---------------------------------------------------
# /cancel - Cancel Login Process
# ---------------------------------------------------
@Client.on_message(filters.private & filters.command(["cancel", "cancellogin"]))
async def cancel_login(client: Client, message: Message):
    user_id = message.from_user.id
   
    if user_id in LOGIN_STATE:
        state = LOGIN_STATE[user_id]
       
        # Disconnect temp client if active
        if "data" in state and "client" in state["data"]:
            try:
                await state["data"]["client"].disconnect()
            except:
                pass
       
        del LOGIN_STATE[user_id]
        await message.reply(
            "<b>❌ Login process cancelled. 😌</b>",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=remove_keyboard
        )
    else:
        pass
# ---------------------------------------------------
# FILTER: Check if user is in Login State
# ---------------------------------------------------
async def check_login_state(_, __, message):
    return message.from_user.id in LOGIN_STATE
login_state_filter = filters.create(check_login_state)
# ---------------------------------------------------
# MAIN LOGIN HANDLER
# Handles Phone -> Code -> Password
# ---------------------------------------------------
@Client.on_message(filters.private & filters.text & login_state_filter & ~filters.command(["cancel", "cancellogin"]))
async def login_handler(bot: Client, message: Message):
    user_id = message.from_user.id
    text = message.text
    state = LOGIN_STATE[user_id]
    step = state["step"]
    progress = PROGRESS_STEPS.get(step, "")
    # Handle "Cancel" button tap
    if text.strip().lower() == "❌ cancel":
        if "data" in state and "client" in state["data"]:
            try:
                await state["data"]["client"].disconnect()
            except:
                pass
        del LOGIN_STATE[user_id]
        await message.reply(
            "<b>❌ Login process cancelled. 😌</b>",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=remove_keyboard
        )
        return
    # STEP 1: WAITING FOR PHONE NUMBER
    if step == "WAITING_PHONE":
        phone_number = text.replace(" ", "")
       
        # Create temporary client
        temp_client = Client(
            name=f"session_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True
        )
       
        status_msg = await message.reply(
            f"<b>🔄 Connecting to Telegram... 🌐</b>\n\n<i>Progress: {progress}</i>",
            parse_mode=enums.ParseMode.HTML
        )
        # Animate loading
        animation_task = asyncio.create_task(animate_loading(status_msg))
       
        await temp_client.connect()
        animation_task.cancel() # Stop animation once connected
       
        try:
            code = await temp_client.send_code(phone_number)
           
            # Save data to state
            state["data"]["client"] = temp_client
            state["data"]["phone"] = phone_number
            state["data"]["hash"] = code.phone_code_hash
            state["step"] = "WAITING_CODE"
            progress = PROGRESS_STEPS["WAITING_CODE"]
           
            await status_msg.edit(
                f"<b>📩 OTP Sent to your app! 📲</b>\n\n"
                f"<i>Progress: {progress}</i>\n\n"
                "Please open your Telegram app and copy the verification code.\n\n"
                "<b>Send it like this:</b> <code>12 345</code> or <code>1 2 3 4 5 6</code>\n\n"
                "<blockquote>Adding spaces helps prevent Telegram from deleting the message automatically. 💡</blockquote>",
                parse_mode=enums.ParseMode.HTML
            )
           
        except PhoneNumberInvalid:
            await status_msg.edit(
                "<b>❌ Oops! Invalid phone number format. 😅</b>\n\n"
                f"<i>Progress: {progress}</i>\n\n"
                "Please try again (e.g., +919876543210).",
                parse_mode=enums.ParseMode.HTML
            )
            await temp_client.disconnect()
            del LOGIN_STATE[user_id]
        except Exception as e:
            await status_msg.edit(
                f"<b>❌ Something went wrong: {e} 🤔</b>\n\n"
                f"<i>Progress: {progress}</i>\n\nPlease try /login again.",
                parse_mode=enums.ParseMode.HTML
            )
            await temp_client.disconnect()
            del LOGIN_STATE[user_id]
    # STEP 2: WAITING FOR OTP CODE
    elif step == "WAITING_CODE":
        phone_code = text.replace(" ", "")
       
        temp_client = state["data"]["client"]
        phone_number = state["data"]["phone"]
        phone_hash = state["data"]["hash"]
       
        status_msg = await message.reply(
            f"<b>🔍 Verifying code... 🔍</b>\n\n<i>Progress: {progress}</i>",
            parse_mode=enums.ParseMode.HTML
        )
        # Short animation for verification
        animation_task = asyncio.create_task(animate_loading(status_msg, duration=3))
       
        try:
            await temp_client.sign_in(phone_number, phone_hash, phone_code)
            animation_task.cancel()
           
            # Direct Success
            await finalize_login(status_msg, temp_client, user_id)
        except PhoneCodeInvalid:
            animation_task.cancel()
            await status_msg.edit(
                "<b>❌ Hmm, that code doesn't look right. 🔍</b>\n\n"
                f"<i>Progress: {progress}</i>\n\nPlease check your Telegram app and try again.",
                parse_mode=enums.ParseMode.HTML
            )
        except PhoneCodeExpired:
            animation_task.cancel()
            await status_msg.edit(
                "<b>⏰ Code has expired. ⏳</b>\n\n"
                f"<i>Progress: {progress}</i>\n\nPlease start over with /login.",
                parse_mode=enums.ParseMode.HTML
            )
            await temp_client.disconnect()
            del LOGIN_STATE[user_id]
        except SessionPasswordNeeded:
            animation_task.cancel()
            # Move to Step 3 (2FA)
            state["step"] = "WAITING_PASSWORD"
            progress = PROGRESS_STEPS["WAITING_PASSWORD"]
            await status_msg.edit(
                f"<b>🔐 Two-Step Verification Detected 🔒</b>\n\n"
                f"<i>Progress: {progress}</i>\n\n"
                "Please enter your account <b>password</b>.\n\n"
                "<i>Take your time — it's secure! 🛡️</i>",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            animation_task.cancel()
            await status_msg.edit(
                f"<b>❌ Something went wrong: {e} 🤔</b>\n\n<i>Progress: {progress}</i>",
                parse_mode=enums.ParseMode.HTML
            )
            await temp_client.disconnect()
            del LOGIN_STATE[user_id]
    # STEP 3: WAITING FOR PASSWORD (2FA)
    elif step == "WAITING_PASSWORD":
        password = text
        temp_client = state["data"]["client"]
       
        status_msg = await message.reply(
            f"<b>🔑 Checking password... 🔑</b>\n\n<i>Progress: {progress}</i>",
            parse_mode=enums.ParseMode.HTML
        )
        # Short animation
        animation_task = asyncio.create_task(animate_loading(status_msg, duration=3))
       
        try:
            await temp_client.check_password(password=password)
            animation_task.cancel()
            await finalize_login(status_msg, temp_client, user_id)
        except PasswordHashInvalid:
            animation_task.cancel()
            await status_msg.edit(
                "<b>❌ Incorrect password. 🔑</b>\n\n"
                f"<i>Progress: {progress}</i>\n\nPlease try again.",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            animation_task.cancel()
            await status_msg.edit(
                f"<b>❌ Something went wrong: {e} 🤔</b>\n\n<i>Progress: {progress}</i>",
                parse_mode=enums.ParseMode.HTML
            )
            await temp_client.disconnect()
            del LOGIN_STATE[user_id]
# ---------------------------------------------------
# FINALIZE LOGIN (Save Session)
# ---------------------------------------------------
async def finalize_login(status_msg: Message, temp_client, user_id):
    try:
        # Generate String Session
        session_string = await temp_client.export_session_string()
        await temp_client.disconnect()
       
        # Save to DB
        await db.set_session(user_id, session=session_string)
       
        # Clear State
        if user_id in LOGIN_STATE:
            del LOGIN_STATE[user_id]
           
        # Success message with "progress bar" complete
        await status_msg.edit(
            "<b>🎉 Login Successful! 🌟</b>\n\n"
            "<i>Progress: ✅ Phone Number → ✅ Code → ✅ Password</i>\n\n"
            "<i>Your session has been saved securely. 🔒</i>\n\n"
            "You can now use all features! 🚀",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=remove_keyboard
        )
    except Exception as e:
        await status_msg.edit(
            f"<b>❌ Failed to save session: {e} 😔</b>\n\nPlease try /login again.",
            parse_mode=enums.ParseMode.HTML,
            reply_markup=remove_keyboard
        )
        if user_id in LOGIN_STATE:
            del LOGIN_STATE[user_id]
