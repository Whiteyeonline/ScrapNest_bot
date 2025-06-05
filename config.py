import telebot
import os
import json # For JSON file persistence
from scraper import scrape_data
from utils import zip_and_send
from payment import verify_payment
from keep_alive import keep_alive
import config # Import config variables
from functools import wraps # For decorator

# --- Constants & Initialization ---
USER_DATA_FILE = 'user_data.json' # File to store user data persistently
LEGAL_TEXT_FILE = 'legal_and_privacy.txt' # File to store legal and privacy text

# Initialize the Telegram bot with token from config
bot = telebot.TeleBot(config.BOT_TOKEN)

# Dictionary to store user-specific data (e.g., remaining uses, ban status)
# This will be loaded from and saved to a JSON file.
user_data = {}

# --- User Data Persistence Functions ---
def load_user_data():
    """Loads user data from a JSON file."""
    global user_data
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f:
                loaded_data = json.load(f)
                # Convert string keys back to int if they represent user IDs
                user_data = {int(k): v for k, v in loaded_data.items()}
            print(f"Loaded user data from {USER_DATA_FILE}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {USER_DATA_FILE}. Starting with empty data.")
            user_data = {}
    else:
        print(f"No {USER_DATA_FILE} found. Starting with empty user data.")
        user_data = {}

def save_user_data():
    """Saves user data to a JSON file."""
    with open(USER_DATA_FILE, 'w') as f:
        # Convert integer keys to strings for JSON serialization
        json.dump({str(k): v for k, v in user_data.items()}, f, indent=4)
    print(f"Saved user data to {USER_DATA_FILE}")

# --- Decorator for Admin-Only Commands ---
def admin_only(func):
    """Decorator to restrict command usage to the ADMIN_ID."""
    @wraps(func)
    def wrapper(message):
        try:
            admin_id_int = int(config.ADMIN_ID) # Ensure ADMIN_ID is an integer for comparison
        except ValueError:
            bot.send_message(message.chat.id, "❌ Admin ID in config is invalid. Please check environment variables.")
            print("Error: ADMIN_ID is not a valid integer.")
            return

        if message.from_user.id == admin_id_int:
            return func(message)
        else:
            bot.send_message(message.chat.id, "🚫 You are not authorized to use this command.")
    return wrapper

# --- Bot Command Handlers ---

@bot.message_handler(commands=['start'])
def start(message):
    """Handles the /start command, sending a welcome message or resetting data."""
    uid = message.from_user.id
    command_parts = message.text.split()

    if len(command_parts) > 1 and command_parts[1].lower() == 'reset':
        # Handle /start reset command
        if uid in user_data:
            if user_data[uid]['banned']:
                bot.send_message(message.chat.id, "🚫 You are currently banned and cannot reset your account.")
                return

            # Reset user data
            user_data[uid]['uses'] = 2
            user_data[uid]['banned'] = False # Ensure not banned after reset
            save_user_data()
            bot.send_message(message.chat.id, "♻️ Your account has been reset! You now have 2 free uses. "
                                              "Use /scrape to begin.")
        else:
            # User is completely new, just provide initial welcome
            bot.send_message(message.chat.id, "👋 Welcome to ScrapNest! You already have 2 free uses. "
                                              "Use /scrape to begin.")
    else:
        # Handle regular /start command
        if uid not in user_data:
            user_data[uid] = {'uses': 2, 'banned': False}
            save_user_data()

        bot.send_message(message.chat.id, "👋 Welcome to ScrapNest!\n\n"
                                          "🔎 Get data from web pages: images, videos, headlines, and prices.\n\n"
                                          "💰 You get 2 free uses. Pay ₹100 to get 15 uses.\n\n"
                                          "Use /scrape to begin.\n"
                                          "Use /uses_left to check your uses left.\n"
                                          "Use /help for more commands.\n"
                                          "Use /legal to view Privacy Policy.\n\n"
                                          "If you cleared your chat and want to reset your uses, send `/start reset`.")


@bot.message_handler(commands=['help'])
def help_command(message):
    """Provides help instructions and lists commands."""
    help_text = "📚 ScrapNest Bot Help:\n\n" \
                "**User Commands:**\n" \
                "/start - Welcome message and info.\n" \
                "/start reset - Reset your account to get 2 new free uses.\n" \
                "/scrape <keyword or URL> - Start a scraping task. (2 free uses, then 15 uses for ₹100)\n" \
                "/uses_left - Check your remaining scraping uses.\n" \
                "/confirm_payment <your PayPal email> - Confirm your payment after sending money.\n" \
                "/legal - View privacy policy and legal notice.\n\n" \
                "**Admin Commands:** (Only for authorized users)\n" \
                "/grant_access <user_id> <uses> - Grant more uses to a user.\n" \
                "/broadcast <message> - Send a message to all users.\n" \
                "/stats - View bot usage statistics.\n" \
                "/ban <user_id> - Ban a user from using the bot.\n" \
                "/unban <user_id> - Unban a previously banned user.\n"
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['legal', 'privacy']) # Handles both /legal and /privacy
def legal_and_privacy(message):
    """Handles the /legal and /privacy commands, displaying privacy policy and legal notice from a file."""
    try:
        with open(LEGAL_TEXT_FILE, 'r', encoding='utf-8') as f:
            legal_text = f.read()
        bot.send_message(message.chat.id, legal_text)
    except FileNotFoundError:
        bot.send_message(message.chat.id, "❌ Legal and privacy policy file not found. Please contact the bot administrator.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ An error occurred while reading the legal policy: {e}")
        print(f"Error reading legal text file: {e}")


@bot.message_handler(commands=['uses_left']) # Renamed from /balance
def uses_left(message):
    """Handles the /uses_left command, showing the user's remaining uses."""
    uid = message.from_user.id
    # Initialize user data if not exists, default uses and not banned
    if uid not in user_data:
        user_data[uid] = {'uses': 2, 'banned': False}
        save_user_data()
    
    if user_data[uid]['banned']:
        bot.send_message(message.chat.id, "🚫 You are currently banned from using this bot.")
        return

    balance = user_data[uid]['uses']
    bot.send_message(message.chat.id, f"💳 You have {balance} uses left.")

@bot.message_handler(commands=['scrape'])
def handle_scrape(message):
    """Initiates the scraping process, checking user uses and ban status first."""
    uid = message.from_user.id
    
    # Initialize user data if not exists
    if uid not in user_data:
        user_data[uid] = {'uses': 2, 'banned': False}
        save_user_data()

    if user_data[uid]['banned']:
        bot.send_message(message.chat.id, "🚫 You are currently banned from using this bot.")
        return

    # Check if the user has any uses left
    if user_data[uid]['uses'] <= 0:
        payment_info = (
            f"💰 To get 15 more uses, please pay ₹100 using one of these methods:\n"
            f"- **PayPal Email:** `{config.PAYPAL_EMAIL}`\n"
            f"- **UPI ID:** `{config.UPI_ID}`\n"
            f"- **Telegram Username:** @{config.TELEGRAM_USERNAME} (User ID: `{config.ADMIN_ID}`)\n\n"
            f"After payment, send: `/confirm_payment <your PayPal email>` (or screenshot if needed for manual verification)."
        )
        bot.send_message(message.chat.id, payment_info, parse_mode='Markdown')
        return
    
    # Prompt user for keyword or URL
    msg = bot.send_message(message.chat.id, "🔍 Send the keyword or URL you want to scrape.")
    # Register the next step handler to process the user's input
    bot.register_next_step_handler(msg, process_scrape)

def process_scrape(message):
    """Processes the user's keyword/URL, initiates scraping, and sends results."""
    uid = message.from_user.id
    keyword = message.text.strip()
    
    # Re-check uses and ban status before processing scrape to prevent abuse
    if uid not in user_data or user_data[uid]['banned'] or user_data[uid]['uses'] <= 0:
        bot.send_message(message.chat.id, "❌ Error: You are not authorized or have no uses left. Please use /uses_left or /scrape again.")
        return

    bot.send_message(message.chat.id, "⏳ Scraping started... This might take a moment.")
    
    try:
        # Call the scrape_data function from scraper.py
        scraped_folder_path = scrape_data(keyword)
        
        # Zip the folder and send it to the user
        zip_and_send(bot, message.chat.id, scraped_folder_path)
        
        # Decrement user's uses after successful scrape
        user_data[uid]['uses'] -= 1
        save_user_data() # Save data after change
        bot.send_message(message.chat.id, f"✅ Scraping complete! You have {user_data[uid]['uses']} uses left.")
    except Exception as e:
        # Catch any errors during scraping or sending and inform the user
        bot.send_message(message.chat.id, f"❌ An error occurred during scraping: {e}")
        print(f"Error in process_scrape for user {uid} with keyword '{keyword}': {e}")

@bot.message_handler(commands=['confirm_payment']) # Renamed from /confirm
def confirm_payment(message):
    """Handles payment confirmation (currently a placeholder)."""
    uid = message.from_user.id
    parts = message.text.split(maxsplit=1) # Split only once to allow spaces in email/details
    if len(parts) < 2:
        bot.send_message(message.chat.id, "❌ Invalid format.\n"
                                          "Use `/confirm_payment <your PayPal email or other details>`\n"
                                          "Example: `/confirm_payment mypaypal@example.com`")
        return
    
    payment_detail = parts[1].strip() # This could be email or a reference to a screenshot/transaction ID

    # IMPORTANT: This is a placeholder for actual payment verification.
    # You MUST replace verify_payment with a real integration (e.g., PayPal API)
    # to check if a payment has actually been received from the given detail.
    # For manual verification, you'd check payment_detail and then manually use /grant_access.
    
    bot.send_message(message.chat.id, 
                     f"Thank you for submitting your payment details: `{payment_detail}`.\n"
                     "Your payment will be manually verified by the admin shortly. Please wait for confirmation."
                     " You can also contact the admin directly: "
                     f"@{config.TELEGRAM_USERNAME} (User ID: `{config.ADMIN_ID}`).",
                     parse_mode='Markdown')
    
    # Optionally, notify admin
    try:
        admin_id_int = int(config.ADMIN_ID)
        bot.send_message(admin_id_int, 
                         f"🔔 New payment confirmation submitted by User ID: `{uid}` (`@{message.from_user.username}`).\n"
                         f"Details: `{payment_detail}`\n"
                         f"Use `/grant_access {uid} 15` to grant uses after verification.",
                         parse_mode='Markdown')
    except ValueError:
        print("Error: ADMIN_ID is not a valid integer. Cannot send admin notification.")
    except Exception as e:
        print(f"Error sending payment notification to admin: {e}")


# --- Admin Commands ---
@bot.message_handler(commands=['grant_access'])
@admin_only
def grant_access(message):
    """Admin command: Grants a number of scraping uses to a specific user."""
    parts = message.text.split()
    if len(parts) != 3:
        bot.send_message(message.chat.id, "❌ Invalid format. Use: `/grant_access <user_id> <uses>`")
        return
    
    try:
        target_uid = int(parts[1])
        uses_to_grant = int(parts[2])
        if uses_to_grant <= 0:
            bot.send_message(message.chat.id, "Uses to grant must be positive.")
            return

        if target_uid not in user_data:
            user_data[target_uid] = {'uses': 0, 'banned': False} # Initialize if new user
        
        user_data[target_uid]['uses'] += uses_to_grant
        save_user_data()
        bot.send_message(message.chat.id, f"✅ Granted {uses_to_grant} uses to user ID `{target_uid}`. New balance: {user_data[target_uid]['uses']}.")
        
        # Notify the target user
        try:
            bot.send_message(target_uid, f"🎉 You have been granted {uses_to_grant} additional scraping uses! Your new total is {user_data[target_uid]['uses']}.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Warning: Could not notify user {target_uid}. Error: {e}")

    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid user ID or number of uses. User: `/grant_access <user_id> <uses>`")

@bot.message_handler(commands=['broadcast'])
@admin_only
def broadcast(message):
    """Admin command: Sends a broadcast message to all users."""
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "❌ Invalid format. Use: `/broadcast <your message>`")
        return
    
    broadcast_message = parts[1].strip()
    sent_count = 0
    failed_count = 0
    
    bot.send_message(message.chat.id, "Starting broadcast...")
    for uid_str in list(user_data.keys()): # Iterate through a copy of keys to avoid modification issues
        try:
            uid = int(uid_str) # Ensure UID is int
            bot.send_message(uid, f"📢 **Announcement from Admin:**\n{broadcast_message}", parse_mode='Markdown')
            sent_count += 1
        except Exception as e:
            print(f"Failed to send broadcast to user {uid_str}: {e}")
            failed_count += 1
    
    bot.send_message(message.chat.id, f"✅ Broadcast complete. Sent to {sent_count} users, failed for {failed_count} users.")

@bot.message_handler(commands=['stats'])
@admin_only
def stats(message):
    """Admin command: Displays bot usage statistics."""
    total_users = len(user_data)
    total_uses_remaining = sum(data.get('uses', 0) for data in user_data.values()) # Sum remaining uses
    banned_users = sum(1 for data in user_data.values() if data.get('banned', False)) # Use .get for safety
    
    stats_text = (
        "📊 Bot Usage Statistics:\n"
        f"👥 Total registered users: `{total_users}`\n"
        f"💳 Total uses remaining across all users: `{total_uses_remaining}`\n"
        f"🚫 Banned users: `{banned_users}`\n\n"
        "*(Note: Statistics are based on current loaded user data.)*"
    )
    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')

@bot.message_handler(commands=['ban'])
@admin_only
def ban_user(message):
    """Admin command: Bans a specified user."""
    parts = message.text.split()
    if len(parts) != 2:
        bot.send_message(message.chat.id, "❌ Invalid format. Use: `/ban <user_id>`")
        return
    
    try:
        target_uid = int(parts[1])
        if target_uid == int(config.ADMIN_ID):
            bot.send_message(message.chat.id, "🚫 You cannot ban yourself.")
            return

        if target_uid not in user_data:
            user_data[target_uid] = {'uses': 0, 'banned': True} # Initialize as banned if new
        else:
            user_data[target_uid]['banned'] = True
        
        save_user_data()
        bot.send_message(message.chat.id, f"✅ User ID `{target_uid}` has been banned.")
        try:
            bot.send_message(target_uid, "🚫 You have been banned from using this bot by the administrator.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Warning: Could not notify user {target_uid}. Error: {e}")

    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid user ID. Use: `/ban <user_id>`")

@bot.message_handler(commands=['unban'])
@admin_only
def unban_user(message):
    """Admin command: Unbans a specified user."""
    parts = message.text.split()
    if len(parts) != 2:
        bot.send_message(message.chat.id, "❌ Invalid format. Use: `/unban <user_id>`")
        return
    
    try:
        target_uid = int(parts[1])
        if target_uid not in user_data:
            bot.send_message(message.chat.id, f"User ID `{target_uid}` not found in records or not banned.")
            return
        
        user_data[target_uid]['banned'] = False
        save_user_data()
        bot.send_message(message.chat.id, f"✅ User ID `{target_uid}` has been unbanned.")
        try:
            bot.send_message(target_uid, "🎉 You have been unbanned by the administrator. You can now use the bot again.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Warning: Could not notify user {target_uid}. Error: {e}")

    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid user ID. Use: `/unban <user_id>`")

# --- Start Bot and Keep-Alive Server ---
if __name__ == '__main__':
    load_user_data() # Load user data at startup
    keep_alive() # Start the Flask web server in a separate thread
    print("Keep-alive server started.")
    
    print("Bot is starting...")
    bot.polling(none_stop=True) # Use none_stop=True to keep bot running
