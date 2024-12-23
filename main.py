# main.py
import os
from keep_alive import keep_alive
from bot import run_bot

BOT_TOKEN = os.environ['BOT_TOKEN']

if __name__ == "__main__":
    keep_alive()
    run_bot(BOT_TOKEN)
