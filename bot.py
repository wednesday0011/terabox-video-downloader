from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import os
import re
import json
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse

async def start_command(update, context):
    await update.message.reply_text('Welcome! Send me a TeraBox link to download videos.')

def is_valid_terabox_url(url):
    """Validate if the URL is a TeraBox link."""
    try:
        parsed = urlparse(url)
        return any(domain in parsed.netloc.lower() 
                  for domain in ['terabox.com', '1024terabox.com', 'www.terabox.com'])
    except:
        return False

async def get_terabox_info(url):
    """Extract necessary info from TeraBox link."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Follow redirects to handle different TeraBox domains
            async with session.get(url, headers=headers, allow_redirects=True) as response:
                if response.status != 200:
                    print(f"Failed to fetch page: {response.status}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find the script containing the video data
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'window.__INITIAL_STATE__' in script.string:
                        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', script.string)
                        if match:
                            try:
                                data = json.loads(match.group(1))
                                file_info = data['file']['list'][0]
                                return {
                                    'fs_id': file_info['fs_id'],
                                    'share_id': data['file']['share_id'],
                                    'sign': data['file']['sign'],
                                    'timestamp': data['file']['timestamp'],
                                    'filename': file_info['filename']
                                }
                            except (KeyError, IndexError, json.JSONDecodeError) as e:
                                print(f"Error parsing JSON data: {e}")
                                return None
                
                print("Could not find __INITIAL_STATE__ in page source")
                return None
                
        except Exception as e:
            print(f"Error getting TeraBox info: {e}")
            return None

async def handle_message(update, context):
    """Handle incoming messages."""
    try:
        if not update.message or not update.message.text:
            return

        text = update.message.text.strip()
        
        if not is_valid_terabox_url(text):
            await update.message.reply_text("Please send a valid TeraBox link (terabox.com or 1024terabox.com).")
            return
        
        # Process download
        status_msg = await update.message.reply_text("Processing TeraBox link... Please wait.")
        
        # Get video info
        info = await get_terabox_info(text)
        if not info:
            await status_msg.edit_text("Could not extract video information. Please check if the link is valid and the content is still available.")
            return
        
        # Rest of the code remains the same...
