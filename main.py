import os
from bot import run_bot

if __name__ == "__main__":
    TOKEN = os.getenv('BOT_TOKEN')
    if TOKEN:
        run_bot(TOKEN)
    else:
        print("No token found!")
