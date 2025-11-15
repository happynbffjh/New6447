import logging
import os
import sys
import json
import signal
import random
import time
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.error import Forbidden
from functools import wraps

# --- Configuration ---
ADMIN_IDS = [6284479489]
BOT_TOKEN = "7875476980:AAGLYnxaDGgjQLELbDRsdgR6aC1wCIDwOCk"
DATA_FILE = "giveaway_data.json"
# --- Bot Logic ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Data Management ---
def load_data():
    """Loads all data from the JSON file."""
    default_data = {
        "codes": {},
        "past_winners": [],
        "users": [],
        "leaderboard": {},
        "banned_users": [],
        "awaiting_screenshot": []
    }
    if not os.path.exists(DATA_FILE):
        save_data(default_data)
        return default_data
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        save_data(default_data)
        return default_data

def save_data(data):
    """Saves all data to the JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- Decorators for Access Control ---
def admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("Sorry, this is an admin-only command.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

def check_banned(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        data = load_data()
        if update.effective_user.id in data["banned_users"]:
            await update.message.reply_text("You have been banned from using this bot.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

# --- User Commands ---
@check_banned
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = load_data()
    if user.id not in data["users"]:
        data["users"].append(user.id)
        save_data(data)
    
    # --- NEW PROFESSIONAL WELCOME MESSAGE ---
    welcome_message = (
        "☁️ **WELCOME TO HEXBREAK VALUT GIVEWAY BOT** ☁️\n\n"
        "☠️**Claim Your Rewards Now!**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "**How to Redeem?**\n"
        "Use the command:\n"
        "💌 `/redeem <CODE>` to claim your reward instantly!\n"
        "💭 /help - To See All Availabe Command\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💥**Don't Miss Out!**\n"
        "Join our official channel for premium giveaways and updates.\n\n"
        "●▬▬๑۩Hαϝιȥυɾ Rαԋɱαɳ۩๑▬▬●"
    )
    
    keyboard = [
        [InlineKeyboardButton("✉️ Contact Owner", url="https://t.me/XD_HR")],
        [InlineKeyboardButton("🚀 Join Channel", url="https://t.me/+wBWZToLvKmBkNDQ1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')


@check_banned
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = load_data()

    if user.id in data["past_winners"]:
        await update.message.reply_text("<b>Sorry, you have already redeemed a prize in this giveaway.</b>", parse_mode='HTML')
        return

    if not context.args:
        await update.message.reply_text("❌ Please provide a code to redeem.")
        return

    code_to_redeem = context.args[0]

    if code_to_redeem in data["codes"]:
        if data["codes"][code_to_redeem]["redeemed_by"] is None:
            user_handle = f"@{user.username}" if user.username else f"User ID: {user.id}"
            data["codes"][code_to_redeem]["redeemed_by"] = user.id
            data["codes"][code_to_redeem]["redeemed_by_username"] = user_handle
            data["past_winners"].append(user.id)

            user_id_str = str(user.id)
            if user_id_str not in data["leaderboard"]:
                data["leaderboard"][user_id_str] = {"username": user_handle, "score": 0}
            data["leaderboard"][user_id_str]["score"] += 1
            data["leaderboard"][user_id_str]["username"] = user_handle

            if user.id not in data["awaiting_screenshot"]:
                data["awaiting_screenshot"].append(user.id)

            save_data(data)

            prize_details = data["codes"][code_to_redeem].get("prize", "Prize details not set. Please contact @Isthiaq_OG")
            success_message = (
                "<b>Congratulations, Mate...!!🎉 You've Got The Prize🔥</b>\n\n"
                f"<code>{prize_details}</code>\n\n"
                "<b>After Login Please Send A Screen In This Bot, I Will Be Glad If You Do It🤝</b>"
            )
            await update.message.reply_html(success_message)

            notification_message = f"<b>🔥 Prize Redeemed! 🔥</b>\n\n<b>User:</b> {user_handle}\n<b>Code:</b> {code_to_redeem}\n<b>Prize:</b> {prize_details}"
            for admin_id in ADMIN_IDS:
                await context.bot.send_message(chat_id=admin_id, text=notification_message, parse_mode='HTML')
        else:
            await update.message.reply_text("😔 Sorry, this code has already been redeemed.")
    else:
        await update.message.reply_text("🤔 That doesn't look like a valid code.")

@check_banned
async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    data = load_data()

    if user.id in data.get("awaiting_screenshot", []):
        user_handle = f"@{user.username}" if user.username else f"User ID: {user.id}"
        caption = f"📸 Screenshot received from {user_handle}"

        for admin_id in ADMIN_IDS:
            try:
                await context.bot.forward_message(chat_id=admin_id, from_chat_id=user.id, message_id=update.message.message_id)
                await context.bot.send_message(chat_id=admin_id, text=caption)
            except Exception as e:
                logger.error(f"Failed to forward screenshot to admin {admin_id}: {e}")

        data["awaiting_screenshot"].remove(user.id)
        save_data(data)

        await update.message.reply_text("✅ Thanks for the screenshot! I've forwarded it to the admin.")
    else:
        await update.message.reply_text("I'm not currently expecting a screenshot from you, but thanks!")


@check_banned
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # --- UPGRADED HELP MENU ---
    help_text = (
        "**Here are the available commands:**\n\n"
        "👤 **User Commands**\n"
        "`/start` - Shows the main welcome menu.\n"
        "`/redeem <code>` - Claim a prize with your code.\n"
        "`/leaderboard` - See the top winners.\n"
        "`/help` - Shows this help message.\n\n"
    )
    if update.effective_user.id in ADMIN_IDS:
        help_text += (
            "👑 **Admin Commands**\n"
            "`/stats` - View bot statistics.\n"
            "`/listcodes` - List all codes and prizes.\n"
            "`/addcode <code>` - Add a new code.\n"
            "`/addprize <code> <prize>` - Set prize for a code.\n"
            "`/delcode <code>` - Delete a code.\n"
            "`/gencode <num> <prefix>` - Generate codes.\n"
            "`/broadcast <msg>` - Send a message to all users.\n"
            "`/ban <user_id>` - Ban a user.\n"
            "`/unban <user_id>` - Unban a user.\n"
            "`/resetgiveaway` - Clear the winner list for a new giveaway.\n"
            "`/stopbot` - Stop the bot."
        )
    await update.message.reply_text(help_text, parse_mode='Markdown')


@check_banned
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = load_data()
    leaderboard_data = data.get("leaderboard", {})
    if not leaderboard_data:
        await update.message.reply_text("The leaderboard is empty.")
        return
    sorted_winners = sorted(leaderboard_data.values(), key=lambda x: x['score'], reverse=True)
    message = "🏆 <b>Giveaway Leaderboard</b> 🏆\n\n"
    for i, winner in enumerate(sorted_winners[:10]):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else ""
        message += f"{medal} {winner['username']}: {winner['score']} wins\n"
    await update.message.reply_html(message)

# --- Admin Panel ---
@admin_only
async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Bot is shutting down...")
    os.kill(os.getpid(), signal.SIGINT)

@admin_only
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = load_data()
    total, redeemed = len(data["codes"]), sum(1 for c in data["codes"].values() if c["redeemed_by"])
    await update.message.reply_html(f"<b>📊 Stats 📊</b>\n\nCodes: {total} total, {redeemed} redeemed, {total - redeemed} available.\nUsers: {len(data['users'])} total, {len(data['banned_users'])} banned.")

@admin_only
async def list_codes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = load_data()
    if not data["codes"]:
        await update.message.reply_text("No codes found.")
        return
    message = "<b>📋 Code Status List 📋</b>\n\n"
    for code, details in data["codes"].items():
        prize_info = f"\n  <i>Prize: {details.get('prize', 'Not set')}</i>"
        if details["redeemed_by"]:
            message += f"• <code>{code}</code>: Redeemed by {details['redeemed_by_username']} ❌{prize_info}\n"
        else:
            message += f"• <code>{code}</code>: <b>Available</b> ✅{prize_info}\n"
    await update.message.reply_html(message)

def initialize_code_details(code):
    return {"redeemed_by": None, "redeemed_by_username": None, "expiry": None, "prize": "No prize set"}

@admin_only
async def add_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /addcode CODE1 [CODE2]...")
        return
    data = load_data()
    added = [c for c in context.args if c not in data["codes"]]
    for code in added:
        data["codes"][code] = initialize_code_details(code)
    if added:
        save_data(data)
        await update.message.reply_text(f"✅ Added {len(added)} code(s).")
    else:
        await update.message.reply_text("No new codes added.")

@admin_only
async def add_prize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addprize [CODE] [The prize details...]")
        return
    code, prize = context.args[0], " ".join(context.args[1:])
    data = load_data()
    if code not in data["codes"]:
        await update.message.reply_text(f"Code `{code}` not found.", parse_mode='MarkdownV2')
        return
    data["codes"][code]["prize"] = prize
    save_data(data)
    await update.message.reply_text(f"✅ Prize for code `{code}` has been set!", parse_mode='MarkdownV2')

@admin_only
async def del_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /delcode CODE1 [CODE2]...")
        return
    data = load_data()
    deleted = [c for c in context.args if c in data["codes"]]
    for code in deleted:
        del data["codes"][code]
    if deleted:
        save_data(data)
        await update.message.reply_text(f"🗑️ Deleted {len(deleted)} code(s).")
    else:
        await update.message.reply_text("No codes deleted.")

@admin_only
async def reset_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = load_data()
    data["past_winners"] = []
    save_data(data)
    await update.message.reply_text("🧹 Giveaway reset! Everyone is eligible again.")

@admin_only
async def gencode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate multiple giveaway codes and prepare for prize assignment."""
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /gencode [amount] [prefix]")
        return

    try:
        amount, prefix = int(context.args[0]), context.args[1].upper()
    except ValueError:
        await update.message.reply_text("❌ Invalid amount.")
        return

    data = load_data()
    generated = []

    for _ in range(amount):
        new_code = f"{prefix}-{random.randint(1000, 9999)}"
        # Initialize full code details
        data["codes"][new_code] = {
            "redeemed_by": None,
            "redeemed_by_username": None,
            "expiry": None,
            "prize": None,  # Will be set after file upload
        }
        generated.append(new_code)

    # Save generated codes for prize assignment
    data["last_generated_codes"] = generated
    save_data(data)

    await update.message.reply_html(
        f"✅ Generated <b>{len(generated)}</b> codes:\n\n"
        + "\n".join(f"<code>{c}</code>" for c in generated)
        + "\n\n📄 Now send a <b>.txt</b> file — each line will be assigned as a prize for each code."
    )

@admin_only
async def handle_admin_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()

    # Check if codes were generated
    if "last_generated_codes" not in data or not data["last_generated_codes"]:
        await update.message.reply_text("⚠️ Please generate codes first using /gencode.")
        return

    if not update.message.document:
        await update.message.reply_text("⚠️ Please send a text file (.txt) containing prize data.")
        return

    # Download the file
    file = await update.message.document.get_file()
    file_path = f"{update.message.document.file_unique_id}.txt"
    await file.download_to_drive(file_path)

    # Read lines from the file safely
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f if line.strip()]

    codes = data["last_generated_codes"]
    assigned = 0

    for i, code in enumerate(codes):
        if i < len(lines):
            data["codes"][code]["prize"] = lines[i]
            assigned += 1
        else:
            data["codes"][code]["prize"] = "No prize set"

    save_data(data)
    await update.message.reply_text(f"✅ Stored {assigned} lines into {len(codes)} codes successfully!")
    
@admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = " ".join(context.args)
    if not message:
        await update.message.reply_text("Usage: /broadcast [your message]")
        return
    data = load_data()
    user_ids = data.get("users", [])
    await update.message.reply_text(f"📢 Starting broadcast to {len(user_ids)} user(s)...")
    success, fail = 0, 0
    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success += 1
            await asyncio.sleep(0.1)
        except Exception:
            fail += 1
    await update.message.reply_text(f"Broadcast finished!\n✅ Success: {success}\n❌ Failed: {fail}")

@admin_only
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /ban [user_id]")
        return
    try:
        user_id_to_ban = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid User ID.")
        return
    data = load_data()
    if user_id_to_ban not in data["banned_users"]:
        data["banned_users"].append(user_id_to_ban)
        save_data(data)
        await update.message.reply_text(f"🚫 User {user_id_to_ban} has been banned.")
    else:
        await update.message.reply_text(f"User {user_id_to_ban} is already banned.")

@admin_only
async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /unban [user_id]")
        return
    try:
        user_id_to_unban = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid User ID.")
        return
    data = load_data()
    if user_id_to_unban in data["banned_users"]:
        data["banned_users"].remove(user_id_to_unban)
        save_data(data)
        await update.message.reply_text(f"✅ User {user_id_to_unban} has been unbanned.")
    else:
        await update.message.reply_text(f"User {user_id_to_unban} was not found in the ban list.")

def main() -> None:
    """Start the bot and all its features."""
    if not BOT_TOKEN:
        logger.error("FATAL: BOT_TOKEN environment variable not set.")
        sys.exit(1)
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("redeem", redeem))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))
    application.add_handler(MessageHandler(filters.Document.ALL & filters.User(ADMIN_IDS), handle_admin_file))

    admin_handlers = [
        CommandHandler("stopbot", stop_bot), CommandHandler("stats", stats),
        CommandHandler("listcodes", list_codes), CommandHandler("addcode", add_code),
        CommandHandler("addprize", add_prize), CommandHandler("delcode", del_code),
        CommandHandler("resetgiveaway", reset_giveaway), CommandHandler("gencode", gencode),
        CommandHandler("broadcast", broadcast), CommandHandler("ban", ban_user),
        CommandHandler("unban", unban_user)
    ]
    application.add_handlers(admin_handlers)

    logger.info("Bot is starting with Professional UI...")
    application.run_polling()

if __name__ == "__main__":
    main()