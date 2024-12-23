from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import os
import re
import json
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import unquote

async def start_command(update, context):
    await update.message.reply_text('Welcome! Send me a TeraBox link to download videos.')

async def get_terabox_info(url):
    """Extract necessary info from TeraBox link."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find the script containing the video data
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'window.__INITIAL_STATE__' in script.string:
                        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', script.string)
                        if match:
                            data = json.loads(match.group(1))
                            try:
                                file_info = data['file']['list'][0]
                                return {
                                    'fs_id': file_info['fs_id'],
                                    'share_id': data['file']['share_id'],
                                    'sign': data['file']['sign'],
                                    'timestamp': data['file']['timestamp'],
                                    'filename': file_info['filename']
                                }
                            except (KeyError, IndexError):
                                return None
                return None
                
        except Exception as e:
            print(f"Error getting TeraBox info: {e}")
            return None

async def get_download_link(info):
    """Get the actual download link using the extracted info."""
    if not info:
        return None
        
    try:
        url = "https://www.terabox.com/share/link"
        params = {
            "surl": info['share_id'],
            "sign": info['sign'],
            "timestamp": info['timestamp'],
            "fs_id": info['fs_id']
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    return None
                    
                data = await response.json()
                if data.get('errno') == 0 and data.get('dlink'):
                    return unquote(data['dlink'])
                    
        return None
        
    except Exception as e:
        print(f"Error getting download link: {e}")
        return None

async def download_video(url, filename, update, context):
    """Download the video and send it to the user."""
    try:
        progress_message = await update.message.reply_text("Starting download... 0%")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    await progress_message.edit_text("Failed to download video.")
                    return False
                
                # Get file size
                file_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                # Download with progress updates
                with open(filename, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024*1024):  # 1MB chunks
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress = (downloaded / file_size) * 100
                            if progress % 5 < 1:  # Update every 5%
                                await progress_message.edit_text(f"Downloading... {progress:.1f}%")
                
                # Send video to user
                await progress_message.edit_text("Upload to Telegram in progress...")
                with open(filename, 'rb') as video:
                    await update.message.reply_video(
                        video=video,
                        filename=filename,
                        caption="Here's your video! 🎥"
                    )
                
                # Cleanup
                os.remove(filename)
                await progress_message.delete()
                return True
                
    except Exception as e:
        print(f"Error downloading video: {e}")
        await update.message.reply_text("Sorry, there was an error downloading the video.")
        if os.path.exists(filename):
            os.remove(filename)
        return False

async def handle_message(update, context):
    """Handle incoming messages."""
    try:
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()
        
        if "terabox.com" not in text.lower():
            await update.message.reply_text("Please send a valid TeraBox link.")
            return
        
        # Process download
        status_msg = await update.message.reply_text("Processing TeraBox link... Please wait.")
        
        # Get video info
        info = await get_terabox_info(text)
        if not info:
            await status_msg.edit_text("Could not extract video information. Please check the link.")
            return
        
        # Get download link
        await status_msg.edit_text("Getting download link...")
        download_link = await get_download_link(info)
        if not download_link:
            await status_msg.edit_text("Could not get download link. Please try again.")
            return
        
        # Download and send video
        await status_msg.edit_text("Starting download process...")
        filename = f"terabox_{info['filename']}"
        success = await download_video(download_link, filename, update, context)
        
        if success:
            await status_msg.delete()
        else:
            await status_msg.edit_text("Failed to process video. Please try again later.")
            
    except Exception as e:
        print(f"Error handling message: {e}")
        await update.message.reply_text("Sorry, something went wrong. Please try again later.")

async def error(update, context):
    """Handle errors."""
    print(f'Update {update} caused error {context.error}')

def run_bot(token):
    """Initialize and run the bot."""
    print('Starting bot...')
    try:
        app = ApplicationBuilder().token(token).build()

        # Add handlers
        app.add_handler(CommandHandler('start', start_command))
        app.add_handler(MessageHandler(filters.TEXT, handle_message))
        app.add_error_handler(error)

        # Start bot
        print('Bot is running...')
        app.run_polling(poll_interval=1)
        
    except Exception as e:
        print(f"Error starting bot: {e}")

if __name__ == "__main__":
    TOKEN = os.getenv('BOT_TOKEN')
    if TOKEN:
        run_bot(TOKEN)
    else:
        print("No token found!")
