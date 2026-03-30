import time
import logging
import os
import re
from telegram import Bot
from dotenv import load_dotenv
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
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        self.coinbase_handle = "CoinbaseMarkets"
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
            "contract address"
        ]
        
        self.telegram_bot = Bot(token=self.telegram_token)
    
    def get_tweets(self):
        """Fetch recent tweets from Coinbase Markets"""
        try:
            logger.info(f"Fetching tweets from @{self.coinbase_handle}...")
            
            # Use Twitter API v2 with user_tweets endpoint (requires less permissions)
            url = "https://api.twitter.com/2/users/by/username/CoinbaseMarkets"
            headers = {"Authorization": f"Bearer {self.twitter_bearer_token}"}
            
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Error getting user: {response.status_code} - {response.text}")
                return
            
            user_data = response.json()
            user_id = user_data['data']['id']
            
            # Now get user's recent tweets
            tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=100&tweet.fields=created_at"
            response = requests.get(tweets_url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Error getting tweets: {response.status_code} - {response.text}")
                return
            
            tweets_data = response.json()
            
            if 'data' not in tweets_data:
                logger.info("No tweets found")
                return
            
            for tweet in tweets_data['data']:
                tweet_id = tweet['id']
                
                if tweet_id in self.processed_tweets:
                    continue
                
                if self._is_listing_announcement(tweet['text']):
                    logger.info(f"Found listing: {tweet['text'][:80]}")
                    
                    token_symbol = self._extract_token_symbol(tweet['text'])
                    self._send_alert(
                        tweet['text'],
                        token_symbol,
                        f"https://x.com/CoinbaseMarkets/status/{tweet_id}",
                        tweet['created_at']
                    )
                    
                    self.processed_tweets.add(tweet_id)
        
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
    
    def _is_listing_announcement(self, text):
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.listing_keywords)
    
    def _extract_token_symbol(self, text):
        matches = re.findall(r'\(([A-Z]+)\)', text)
        if matches:
            return matches[0]
        
        words = text.split()
        for word in words:
            if len(word) >= 3 and len(word) <= 6 and word.isupper():
                return word
        
        return "NEW_TOKEN"
    
    def _send_alert(self, text, symbol, url, timestamp):
        try:
            message = f"""
🚀 **COINBASE LISTING DETECTED**

📌 Token: `{symbol}`

📝 Announcement:
{text}

🔗 Tweet: {url}

⏰ Time: {timestamp}
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
        logger.info("🤖 Coinbase Listing Bot started!")
        
        while True:
            try:
                self.get_tweets()
                logger.info("Waiting 60 seconds...")
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                time.sleep(60)

def main():
    tracker = CoinbaseListingTracker()
    tracker.run()

if __name__ == "__main__":
    main()
