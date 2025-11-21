# daily_grok_solana_degen_bot.py
# Fully automated X bot powered by Grok-4
# Posts every day at 09:00 UTC

import requests
import tweepy
import schedule
import time
import os
from datetime import datetime
import logging

# ============================
# CONFIGURATION - FILL THESE IN
# ============================

# xAI Grok API (get yours at https://x.ai/api once you have access)
GROK_API_KEY = "xai_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # ← YOUR GROK API KEY
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

# X (Twitter) API v2 credentials (create a bot account + dev app at developer.twitter.com)
X_BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAA..."          # From your app
X_API_KEY = "YOUR_API_KEY"
X_API_SECRET = "YOUR_API_SECRET"
X_ACCESS_TOKEN = "BOT_ACCESS_TOKEN"
X_ACCESS_SECRET = "BOT_ACCESS_SECRET"

# Optional: Telegram alert (if you want a copy in your private group)
TELEGRAM_BOT_TOKEN = ""      # Leave empty to disable
TELEGRAM_CHAT_ID = ""        # Leave empty to disable

# Bot handle (for branding)
BOT_NAME = "@SolanaDegenGrok"

# ============================
# SETUP LOGGING
# ============================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# ============================
# X CLIENT SETUP
# ============================

client_v2 = tweepy.Client(
    bearer_token=X_BEARER_TOKEN,
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_SECRET,
    wait_on_rate_limit=True
)

# For media upload (v1.1 API still needed)
auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
api_v1 = tweepy.API(auth)

# ============================
# GROK PROMPT (the magic)
# ============================

GROK_PROMPT = """
You are the Grok Meme Threat Intelligence Lab.
Run the full upgraded Solana memecoin scanner right now (last 6 hours only).
Return:
1. A top-10 leaderboard image (neon cyberpunk style) with rank, ticker, age, hype score, rug risk, $1k ape simulator
2. A deep-dive image of the current #1 coin with meme evolution timeline + exploding neon candlestick chart
3. The exact tweet thread text (3 tweets max) with perfect formatting, emojis, and LFG energy
4. Two image files: leaderboard.png and deepdive.png

Output format:
===THREAD_TEXT===
[full thread text with ||| separators for each tweet]
===END_THREAD===

Then attach the two images.
"""

# ============================
# MAIN FUNCTION
# ============================

def generate_daily_report():
    logger.info("Generating daily Grok Solana degen report...")
    
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "grok-4",
        "messages": [{"role": "user", "content": GROK_PROMPT}],
        "temperature": 0.8,
        "max_tokens": 4096
    }
    
    try:
        response = requests.post(GROK_API_URL, json=payload, headers=headers, timeout=180)
        response.raise_for_status()
        data = response.json()
        
        # Grok returns images as base64 or URLs depending on version
        # This works with current early access format
        content = data["choices"][0]["message"]["content"]
        
        # Extract thread text
        if "===THREAD_TEXT===" in content:
            thread_text = content.split("===THREAD_TEXT===")[1].split("===END_THREAD===")[0].strip()
        else:
            thread_text = content[:1000] + "\n\nDaily alpha from Grok 🚀\nFollow for more"
        
        # Extract images (Grok API returns them in "images" field or attachments)
        images = []
        if "images" in data["choices"][0]["message"]:
            for img in data["choices"][0]["message"]["images"]:
                img_data = img["data"] if "data" in img else img["url"]
                images.append(("leaderboard.png" if "leaderboard" in str(img) else "deepdive.png", img_data))
        
        return thread_text, images
    
    except Exception as e:
        logger.error(f"Grok API error: {e}")
        return None, None

def post_to_x():
    logger.info("Starting daily post sequence...")
    
    thread_text, images = generate_daily_report()
    if not thread_text or not images:
        logger.error("Failed to generate report. Skipping post.")
        return
    
    # Save images temporarily
    image_paths = []
    media_ids = []
    
    try:
        for i, (filename, img_data) in enumerate(images[:2]):  # Max 2 images for thread
            path = f"/tmp/{filename}"
            with open(path, "wb") as f:
                if img_data.startswith("http"):
                    f.write(requests.get(img_data).content)
                else:
                    f.write(requests.get(f"data:image/png;base64,{img_data}").content)
            image_paths.append(path)
            
            # Upload to X
            media = api_v1.media_upload(path)
            media_ids.append(media.media_id)
        
        # Split thread
        tweets = [t.strip() for t in thread_text.split("|||") if t.strip()]
        if not tweets:
            tweets = [thread_text[:275] + "…"]
        
        # Post first tweet
        first_tweet = client_v2.create_tweet(
            text=tweets[0] + f"\n\n{BOT_NAME} | {datetime.utcnow().strftime('%b %d, %Y')}",
            media_ids=media_ids
        )
        logger.info("Posted main tweet!")
        
        parent_id = first_tweet.data["id"]
        
        # Post replies if any
        for tweet in tweets[1:]:
            reply = client_v2.create_tweet(
                text=tweet,
                in_reply_to_tweet_id=parent_id,
                media_ids=[]  # No extra media in replies
            )
            parent_id = reply.data["id"]
        
        logger.info("Daily degen report posted successfully! 🚀")
        
        # Optional: Send to Telegram
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": tweets[0]},
                files={"photo": open(image_paths[0], "rb")}
            )
    
    except Exception as e:
        logger.error(f"Posting failed: {e}")
    
    finally:
        # Clean up
        for path in image_paths:
            if os.path.exists(path):
                os.remove(path)

# ============================
# SCHEDULER
# ============================

schedule.every().day.at("09:00").do(post_to_x)  # 9:00 AM UTC = prime CT time

# Optional: Test run immediately on startup
if __name__ == "__main__":
    logger.info("Grok Solana Degen Bot starting...")
    logger.info("First post in test mode...")
    post_to_x()  # Remove this line after first successful test
    
    logger.info("Now entering daily schedule mode (9:00 UTC)...")
    while True:
        schedule.run_pending()
        time.sleep(30)
