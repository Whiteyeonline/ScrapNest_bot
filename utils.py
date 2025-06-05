import shutil
import os

def zip_and_send(bot, chat_id, folder_to_zip):
    """
    Zips the specified folder and sends the zip file to the user.
    After sending, it cleans up the created zip file and the original folder.
    """
    # Ensure the folder exists before trying to zip
    if not os.path.exists(folder_to_zip):
        bot.send_message(chat_id, f"❌ Error: Scraped data folder '{folder_to_zip}' not found.")
        return

    # Create the zip file path. The base_name will be the name of the zip file
    # (without .zip extension), which is derived from the folder name.
    zip_base_name = folder_to_zip 
    zip_path = f"{zip_base_name}.zip"

    try:
        # Create the zip archive.
        # shutil.make_archive(base_name, format, root_dir, base_dir)
        # - base_name: The name of the archive file to create, including the path.
        # - format: The archive format (e.g., 'zip', 'tar').
        # - root_dir: The directory from which to start archiving.
        # - base_dir: The directory inside root_dir that will be archived.
        shutil.make_archive(zip_base_name, 'zip', os.path.dirname(folder_to_zip), os.path.basename(folder_to_zip))
        
        # Send the zip file to the user.
        with open(zip_path, "rb") as f:
            bot.send_document(chat_id, f)
        
        bot.send_message(chat_id, "📤 Your scraped data has been sent as a zip file!")

    except Exception as e:
        print(f"Error zipping or sending file: {e}")
        bot.send_message(chat_id, "❌ An error occurred while zipping or sending your data.")
    finally:
        # Clean up: remove the created zip file and the original folder to save disk space.
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(folder_to_zip):
            shutil.rmtree(folder_to_zip) # Remove the folder and its contents recursively

# The check_balance function is not directly used in bot.py anymore,
# as user_data handling is now more centralized.
# It's kept here for completeness in case you decide to use it elsewhere.
def check_balance(user_data, uid):
    """Returns the current balance for a user."""
    return user_data.get(uid, {'uses': 2}).get('uses', 2)
            
