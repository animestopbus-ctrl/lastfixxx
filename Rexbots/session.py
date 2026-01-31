import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
    FloodWait
)
from pyrogram import enums
from config import API_ID, API_HASH
from database.db import db

# ==========================================
# STATE MANAGEMENT
# Stores temporary login data
# {user_id: {"step": "WAITING_PHONE", "data": {...}, "status_msg_id": int}}
# Added status_msg_id to track and edit the progress message dynamically
# ==========================================
LOGIN_STATE = {}

# Keyboards
cancel_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("❌ Cancel")]],
    resize_keyboard=True
)
remove_keyboard = ReplyKeyboardRemove()

# Progress steps with emoji indicators
PROGRESS_STEPS = {
    "WAITING_PHONE": "🟢 Phone Number → 🔵 Code → 🔵 Password",
    "WAITING_CODE": "✅ Phone Number → 🟢 Code → 🔵 Password",
    "WAITING_PASSWORD": "✅ Phone Number → ✅ Code → 🟢 Password",
    "COMPLETE": "✅ Phone Number → ✅ Code → ✅ Password"
}

# Enhanced progress bar frames for each step (dynamic filling)
PROGRESS_BARS = [
    "░░░░░░░░░░ 0%",   # Empty
    "█░░░░░░░░░ 10%",
    "██░░░░░░░░ 20%",
    "███░░░░░░░ 30%",
    "████░░░░░░ 40%",
    "█████░░░░░ 50%",
    "██████░░░░ 60%",
    "███████░░░ 70%",
    "████████░░ 80%",
    "█████████░ 90%",
    "██████████ 100%"  # Full
]

# Emoji-based loading animation frames (enhanced with more frames for smoothness)
LOADING_FRAMES = [
    "🔄 Connecting •••",
    "🔄 Connecting ••○",
    "🔄 Connecting •○○",
    "🔄 Connecting ○○○",
    "🔄 Connecting ○○•",
    "🔄 Connecting ○••",
    "🔄 Connecting •••",
    "🔄 Connecting ○••",
    "🔄 Connecting ○○•",
    "🔄 Connecting ○○○"
]

async def animate_loading(client: Client, chat_id: int, msg_id: int, duration: int = 5):
    """Animate a loading message for a specified duration with smoother transitions."""
    end_time = time.time() + duration
    frame_index = 0
    while time.time() < end_time:
        frame = LOADING_FRAMES[frame_index % len(LOADING_FRAMES)]
        try:
            await client.edit_message_text(chat_id, msg_id, f"<b>{frame}</b>", parse_mode=enums.ParseMode.HTML)
            await asyncio.sleep(0.3)  # Smoother animation speed
            frame_index += 1
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
        except Exception:
            return

async def update_progress(client: Client, chat_id: int, msg_id: int, step: str, additional_text: str = ""):
    """Dynamically update the progress message with bar and steps."""
    progress_text = PROGRESS_STEPS.get(step, PROGRESS_STEPS["WAITING_PHONE"])
    # Determine bar index based on step
    if step == "WAITING_PHONE":
        bar_index = 3  # 30%
    elif step == "WAITING_CODE":
        bar_index = 6  # 60%
    elif step == "WAITING_PASSWORD":
        bar_index = 8  # 80%
    elif step == "COMPLETE":
        bar_index = 10  # 100%
    else:
        bar_index = 0
    
    bar = PROGRESS_BARS[bar_index]
    text = f"<b>Progress: [{bar}]</b>\n<i>{progress_text}</i>\n\n{additional_text}"
    try:
        await client.edit_message_text(chat_id, msg_id, text, parse_mode=enums.ParseMode.HTML)
    except FloodWait as fw:
        await asyncio.sleep(fw.value)
    except Exception as e:
        pass  # Silent fail to avoid breaking

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
    
    # Send initial progress message
    status_msg = await message.reply(
        "<b>👋 Hey! Let's log you in smoothly 🌟</b>\n\n"
        "<i>Progress: [░░░░░░░░░░ 0%] 🟢 Phone Number → 🔵 Code → 🔵 Password</i>\n\n"
        "📞 Please send your <b>Telegram Phone Number</b> with country code.\n\n"
        "<blockquote>Example: +919876543210</blockquote>\n\n"
        "<i>💡 Your number is used only for verification and is kept secure. 🔒</i>\n\n"
        "❌ Tap the <b>Cancel</b> button or send /cancel to stop.",
        parse_mode=enums.ParseMode.HTML,
        reply_markup=cancel_keyboard
    )
    LOGIN_STATE[user_id]["status_msg_id"] = status_msg.id

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
# Handles Phone -> Code -> Password with enhanced safety and UI
# ---------------------------------------------------
@Client.on_message(filters.private & filters.text & login_state_filter & ~filters.command(["cancel", "cancellogin"]))
async def login_handler(client: Client, message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    state = LOGIN_STATE[user_id]
    step = state["step"]
    chat_id = message.chat.id
    status_msg_id = state.get("status_msg_id")
    
    # Handle "Cancel" button tap
    if text.lower() == "❌ cancel":
        if "data" in state and "client" in state["data"]:
            try:
                await state["data"]["client"].disconnect()
            except:
                pass
        del LOGIN_STATE[user_id]
        await client.edit_message_text(chat_id, status_msg_id, "<b>❌ Login process cancelled. 😌</b>", parse_mode=enums.ParseMode.HTML)
        await message.reply(" ", reply_markup=remove_keyboard)  # To remove keyboard
        return
    
    # STEP 1: WAITING FOR PHONE NUMBER
    if step == "WAITING_PHONE":
        phone_number = text.replace(" ", "")
        
        # Enhanced Validation: Check if starts with + and is digits
        if not phone_number.startswith('+') or not phone_number[1:].isdigit():
            await update_progress(client, chat_id, status_msg_id, step, "<b>❌ Invalid format! Please use + followed by digits (e.g., +919876543210).</b>")
            return
        
        # Create temporary client
        temp_client = Client(
            name=f"session_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True
        )
        
        # Update progress to loading
        await update_progress(client, chat_id, status_msg_id, step, "<b>🔄 Connecting to Telegram... 🌐</b>")
        
        # Animate loading with safety
        animation_task = asyncio.create_task(animate_loading(client, chat_id, status_msg_id, duration=5))
        
        try:
            await temp_client.connect()
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
            await temp_client.connect()
        except Exception as e:
            animation_task.cancel()
            await update_progress(client, chat_id, status_msg_id, step, f"<b>❌ Connection failed: {e}. Please try again.</b>")
            del LOGIN_STATE[user_id]
            return
        
        animation_task.cancel()  # Stop animation once connected
        
        try:
            code = await temp_client.send_code(phone_number)
            
            # Save data to state
            state["data"]["client"] = temp_client
            state["data"]["phone"] = phone_number
            state["data"]["hash"] = code.phone_code_hash
            state["step"] = "WAITING_CODE"
            
            additional_text = "<b>📩 OTP Sent to your app! 📲</b>\n\n" \
                              "Please open your Telegram app and copy the verification code.\n\n" \
                              "<b>Send it like this:</b> <code>12 345</code> or <code>1 2 3 4 5 6</code>\n\n" \
                              "<blockquote>Adding spaces helps prevent Telegram from deleting the message automatically. 💡</blockquote>"
            await update_progress(client, chat_id, status_msg_id, "WAITING_CODE", additional_text)
            
        except PhoneNumberInvalid:
            await update_progress(client, chat_id, status_msg_id, step, "<b>❌ Oops! Invalid phone number. 😅 Please try again (e.g., +919876543210).</b>")
            await temp_client.disconnect()
            del LOGIN_STATE[user_id]
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
            # Retry logic if needed
            await update_progress(client, chat_id, status_msg_id, step, "<b>⚠️ Rate limit hit. Retrying after delay...</b>")
            # Assuming retry once
            try:
                code = await temp_client.send_code(phone_number)
                # Proceed as above
            except:
                await update_progress(client, chat_id, status_msg_id, step, "<b>❌ Failed after retry. Please try later.</b>")
                await temp_client.disconnect()
                del LOGIN_STATE[user_id]
        except Exception as e:
            await update_progress(client, chat_id, status_msg_id, step, f"<b>❌ Something went wrong: {e} 🤔 Please try /login again.</b>")
            await temp_client.disconnect()
            del LOGIN_STATE[user_id]
    
    # STEP 2: WAITING FOR OTP CODE
    elif step == "WAITING_CODE":
        phone_code = text.replace(" ", "")
        
        # Validate: Should be digits only
        if not phone_code.isdigit():
            await update_progress(client, chat_id, status_msg_id, step, "<b>❌ Invalid code! Please send digits only (with spaces if needed).</b>")
            return
        
        temp_client = state["data"]["client"]
        phone_number = state["data"]["phone"]
        phone_hash = state["data"]["hash"]
        
        await update_progress(client, chat_id, status_msg_id, step, "<b>🔍 Verifying code... 🔍</b>")
        
        animation_task = asyncio.create_task(animate_loading(client, chat_id, status_msg_id, duration=3))
        
        try:
            await temp_client.sign_in(phone_number, phone_hash, phone_code)
            animation_task.cancel()
            
            # Direct Success
            await finalize_login(client, chat_id, status_msg_id, temp_client, user_id)
        except PhoneCodeInvalid:
            animation_task.cancel()
            await update_progress(client, chat_id, status_msg_id, step, "<b>❌ Hmm, that code doesn't look right. 🔍 Please check and try again.</b>")
        except PhoneCodeExpired:
            animation_task.cancel()
            await update_progress(client, chat_id, status_msg_id, step, "<b>⏰ Code has expired. ⏳ Please start over with /login.</b>")
            await temp_client.disconnect()
            del LOGIN_STATE[user_id]
        except SessionPasswordNeeded:
            animation_task.cancel()
            state["step"] = "WAITING_PASSWORD"
            additional_text = "<b>🔐 Two-Step Verification Detected 🔒</b>\n\n" \
                              "Please enter your account <b>password</b>.\n\n" \
                              "<i>Take your time — it's secure! 🛡️</i>"
            await update_progress(client, chat_id, status_msg_id, "WAITING_PASSWORD", additional_text)
        except FloodWait as fw:
            animation_task.cancel()
            await asyncio.sleep(fw.value)
            await update_progress(client, chat_id, status_msg_id, step, "<b>⚠️ Rate limit hit. Retrying...</b>")
            try:
                await temp_client.sign_in(phone_number, phone_hash, phone_code)
                await finalize_login(client, chat_id, status_msg_id, temp_client, user_id)
            except:
                await update_progress(client, chat_id, status_msg_id, step, "<b>❌ Verification failed after retry.</b>")
                await temp_client.disconnect()
                del LOGIN_STATE[user_id]
        except Exception as e:
            animation_task.cancel()
            await update_progress(client, chat_id, status_msg_id, step, f"<b>❌ Something went wrong: {e} 🤔</b>")
            await temp_client.disconnect()
            del LOGIN_STATE[user_id]
    
    # STEP 3: WAITING FOR PASSWORD (2FA)
    elif step == "WAITING_PASSWORD":
        password = text
        temp_client = state["data"]["client"]
        
        await update_progress(client, chat_id, status_msg_id, step, "<b>🔑 Checking password... 🔑</b>")
        
        animation_task = asyncio.create_task(animate_loading(client, chat_id, status_msg_id, duration=3))
        
        try:
            await temp_client.check_password(password=password)
            animation_task.cancel()
            await finalize_login(client, chat_id, status_msg_id, temp_client, user_id)
        except PasswordHashInvalid:
            animation_task.cancel()
            await update_progress(client, chat_id, status_msg_id, step, "<b>❌ Incorrect password. 🔑 Please try again.</b>")
        except FloodWait as fw:
            animation_task.cancel()
            await asyncio.sleep(fw.value)
            await update_progress(client, chat_id, status_msg_id, step, "<b>⚠️ Rate limit hit. Retrying...</b>")
            try:
                await temp_client.check_password(password=password)
                await finalize_login(client, chat_id, status_msg_id, temp_client, user_id)
            except:
                await update_progress(client, chat_id, status_msg_id, step, "<b>❌ Password check failed after retry.</b>")
                await temp_client.disconnect()
                del LOGIN_STATE[user_id]
        except Exception as e:
            animation_task.cancel()
            await update_progress(client, chat_id, status_msg_id, step, f"<b>❌ Something went wrong: {e} 🤔</b>")
            await temp_client.disconnect()
            del LOGIN_STATE[user_id]

# ---------------------------------------------------
# FINALIZE LOGIN (Save Session)
# ---------------------------------------------------
async def finalize_login(client: Client, chat_id: int, status_msg_id: int, temp_client, user_id):
    try:
        # Generate String Session
        session_string = await temp_client.export_session_string()
        await temp_client.disconnect()
        
        # Save to DB
        await db.set_session(user_id, session=session_string)
        
        # Clear State
        if user_id in LOGIN_STATE:
            del LOGIN_STATE[user_id]
        
        # Success message with complete progress bar
        await update_progress(client, chat_id, status_msg_id, "COMPLETE", "<b>🎉 Login Successful! 🌟</b>\n\n" \
                      "<i>Your session has been saved securely. 🔒</i>\n\n" \
                      "You can now use all features! 🚀")
        # Remove keyboard
        await client.send_message(chat_id, " ", reply_markup=remove_keyboard)
    except Exception as e:
        await update_progress(client, chat_id, status_msg_id, "WAITING_PASSWORD", f"<b>❌ Failed to save session: {e} 😔</b>\n\nPlease try /login again.")
        if user_id in LOGIN_STATE:
            del LOGIN_STATE[user_id]
