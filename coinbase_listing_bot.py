import time
import logging
import os
import re
from telegram import Bot
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CoinbaseListingTracker:
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        self.nitter_urls = [
            "https://nitter.net/CoinbaseMarkets",
            "https://nitter.1d4.us/CoinbaseMarkets",
            "https://nitter.poast.org/CoinbaseMarkets"
        ]
        
        self.processed_tweets = set()
        
        self.listing_keywords = [
            "PRE listing",
            "trading goes live",
            "now available",
            "now live",
            "auction",
            "spot trading",
            "will go live",
            "available on coinbase",
            "trading pair",
            "limit-only mode",
            "enter auction mode",
            "contract address",
            "assets added"
        ]
        
        self.telegram_bot = Bot(token=self.telegram_token)
    
    def get_tweets_from_nitter(self):
        """Fetch tweets from Nitter (free Twitter scraper)"""
        try:
            logger.info("Fetching tweets from Nitter...")
            
            for nitter_url in self.nitter_urls:
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    response = requests.get(nitter_url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find all tweet containers
                    tweets = soup.find_all('div', class_='tweet')
                    
                    if not tweets:
                        logger.warning(f"No tweets found on {nitter_url}")
                        continue
                    
                    logger.info(f"Found {len(tweets)} tweets from {nitter_url}")
                    
                    for tweet in tweets:
                        try:
                            # Get tweet text
                            text_elem = tweet.find('p', class_='tweet-text')
                            if not text_elem:
                                continue
                            
                            tweet_text = text_elem.get_text()
                            
                            # Get tweet link to extract ID
                            link_elem = tweet.find('a', class_='tweet-link')
                            if not link_elem or not link_elem.get('href'):
                                continue
                            
                            tweet_url = link_elem.get('href')
                            tweet_id = tweet_url.split('/')[-1]
                            
                            if tweet_id in self.processed_tweets:
                                continue
                            
                            # Check if it's a listing announcement
                            if self._is_listing_announcement(tweet_text):
                                logger.info(f"🎯 Found listing: {tweet_text[:80]}")
                                
                                token_symbol = self._extract_token_symbol(tweet_text)
                                full_url = f"https://x.com/CoinbaseMarkets/status/{tweet_id}"
                                
                                self._send_alert(tweet_text, token_symbol, full_url)
                                self.processed_tweets.add(tweet_id)
                        
                        except Exception as e:
                            logger.error(f"Error processing tweet: {e}")
                            continue
                    
                    return True  # Successfully got tweets
                
                except Exception as e:
                    logger.warning(f"Error fetching from {nitter_url}: {e}")
                    continue
            
            logger.error("Could not fetch from any Nitter instance")
            return False
        
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return False
    
    def _is_listing_announcement(self, text):
        """Check if tweet contains listing keywords"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.listing_keywords)
    
    def _extract_token_symbol(self, text):
        """Extract token symbol from tweet"""
        matches = re.findall(r'\(([A-Z]+)\)', text)
        if matches:
            return matches[0]
        
        words = text.split()
        for word in words:
            if len(word) >= 3 and len(word) <= 6 and word.isupper():
                return word
        
        return "NEW_TOKEN"
    
    def _send_alert(self, text, symbol, url):
        """Send Telegram alert"""
        try:
            message = f"""
🚀 **COINBASE LISTING DETECTED**

📌 Token: `{symbol}`

📝 Announcement:
{text}

🔗 Tweet: {url}
            """
            
            self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Alert sent for {symbol}")
        except Exception as e:
            logger.error(f"Error sending alert: {e}", exc_info=True)
    
    def run(self):
        """Main loop"""
        logger.info("🤖 Coinbase Listing Bot (Nitter) started!")
        
        while True:
            try:
                self.get_tweets_from_nitter()
                logger.info("Waiting 60 seconds for next check...")
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                time.sleep(60)

def main():
    tracker = CoinbaseListingTracker()
    tracker.run()

if __name__ == "__main__":
    main()
```

Then update **`requirements.txt`** to:
```
tweepy==4.14.0
python-telegram-bot==20.7
python-dotenv==1.0.0
beautifulsoup4==4.12.2
requests==2.31.0
lxml==4.9.3
