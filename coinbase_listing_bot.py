import asyncio
import logging
import os
import re
from datetime import datetime
import tweepy
from telegram import Bot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CoinbaseListingTracker:
    def __init__(self):
        # Twitter/X API credentials
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        # Telegram credentials
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # Coinbase Markets X account
        self.coinbase_markets_handle = "CoinbaseMarkets"
        
        # Listing keywords to track
        self.listing_keywords = [
            "PRE listing",
            "trading goes live",
            "now available",
            "now live",
            "auction",
            "crosses mid",
            "trading begins",
            "listing announcement",
            "will be available"
        ]
        
        # Track processed tweet IDs to avoid duplicates
        self.processed_tweets = set()
        
        # Initialize Twitter client (v2 API)
        self.twitter_client = tweepy.Client(
            bearer_token=self.twitter_bearer_token,
            wait_on_rate_limit=True
        )
        
        # Initialize Telegram bot
        self.telegram_bot = Bot(token=self.telegram_token)
        
    def search_listings(self):
        """Search for listing announcements from Coinbase Markets"""
        try:
            logger.info("Searching for Coinbase Markets listing announcements...")
            
            # Query recent tweets from Coinbase Markets
            query = f"from:{self.coinbase_markets_handle} (listing OR trading OR auction OR available)"
            
            # Get tweets from last hour
            response = self.twitter_client.search_recent_tweets(
                query=query,
                max_results=100,
                tweet_fields=['created_at'],
            )
            
            if response.data is None:
                logger.warning("No tweets found")
                return
            
            # Process tweets
            for tweet in response.data:
                tweet_id = tweet.id
                
                # Skip if already processed
                if tweet_id in self.processed_tweets:
                    continue
                
                # Check if tweet contains listing keywords
                if self._is_listing_announcement(tweet.text):
                    logger.info(f"Found listing announcement: {tweet.text[:100]}")
                    
                    # Extract token symbol
                    token_symbol = self._extract_token_symbol(tweet.text)
                    
                    # Send Telegram alert
                    self._send_telegram_alert(
                        tweet_text=tweet.text,
                        token_symbol=token_symbol,
                        tweet_url=f"https://x.com/{self.coinbase_markets_handle}/status/{tweet_id}",
                        created_at=tweet.created_at
                    )
                    
                    self.processed_tweets.add(tweet_id)
            
        except Exception as e:
            logger.error(f"Error searching listings: {e}", exc_info=True)
    
    def _is_listing_announcement(self, text):
        """Check if tweet text contains listing-related keywords"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.listing_keywords)
    
    def _extract_token_symbol(self, text):
        """Extract token symbol from announcement text"""
        matches = re.findall(r'\(([A-Z]+)\)', text)
        if matches:
            return matches[0]
        
        words = text.split()
        for word in words:
            if len(word) >= 3 and len(word) <= 6 and word.isupper():
                return word
        
        return "NEW_TOKEN"
    
    def _send_telegram_alert(self, tweet_text, token_symbol, tweet_url, created_at):
        """Send Telegram notification"""
        try:
            message = f"""
🚀 **COINBASE LISTING DETECTED**

📌 Token: `{token_symbol}`

📝 Announcement:
{tweet_text}

🔗 Tweet: {tweet_url}

⏰ Time: {created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
            """
            
            self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Telegram alert sent for {token_symbol}")
            
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}", exc_info=True)
    
    def run(self):
        """Main loop: polling"""
        logger.info("🤖 Coinbase Listing Bot started!")
        
        while True:
            try:
                self.search_listings()
                logger.info("Waiting 30 seconds for next check...")
                import time
                time.sleep(30)
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                import time
                time.sleep(60)


def main():
    tracker = CoinbaseListingTracker()
    tracker.run()


if __name__ == "__main__":
    main()
