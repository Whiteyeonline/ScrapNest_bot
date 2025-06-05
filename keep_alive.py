import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    """Simple route to indicate the bot is alive."""
    return "Bot is alive!"

def run():
    """Runs the Flask app on all available interfaces and a dynamic port."""
    # Use 0.0.0.0 to listen on all public IPs
    # Use the PORT environment variable provided by hosting services like Render, default to 8080
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 8080))

def keep_alive():
    """Starts the Flask web server in a separate thread."""
    t = Thread(target=run)
    t.start()
    
