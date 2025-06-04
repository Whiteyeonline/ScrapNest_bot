import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists.
# This is primarily for local development. On deployment platforms like Render,
# environment variables are typically set directly in the platform's configuration.
load_dotenv()

# Your Telegram Bot Token. Get this from BotFather on Telegram.
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Your Telegram User ID. This will be used to identify the bot administrator.
ADMIN_ID = os.getenv("ADMIN_ID") # Set your Telegram User ID here

# Your PayPal email address where you receive payments.
PAYPAL_EMAIL = os.getenv("PAYPAL_EMAIL") # Your PayPal email: www.muneerjahan@gmail.com

# Your UPI ID where you receive payments.
UPI_ID = os.getenv("UPI_ID") # Your UPI ID: www.muneerjahan@okaxis

# Your Telegram Username for contact.
TELEGRAM_USERNAME = os.getenv("TELEGRAM_USERNAME") # Your Telegram username: @muneerjahan

# Ensure the BOT_TOKEN and ADMIN_ID are set, as the bot cannot function without them.
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set. Please set it in your .env file or deployment environment.")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID environment variable not set. Please set it in your .env file or deployment environment.")
# PAYPAL_EMAIL, UPI_ID, TELEGRAM_USERNAME can be None if not using payment features,
# but it's good practice to ensure they are handled if payment is enabled.

