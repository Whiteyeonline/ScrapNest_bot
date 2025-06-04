import os
from scraper import scrape_data
from utils import send_alert
from keep_alive import keep_alive

def start_bot():
    keep_alive()
    print("Bot is running...")
    # Simulated scraping process
    result = scrape_data("https://example.com")
    send_alert("admin@example.com", result)
