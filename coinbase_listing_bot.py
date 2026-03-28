import asyncio
import logging
import os
from datetime import datetime
import aiohttp
import tweepy
import requests
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
        self.twitter_api_key = os.getenv('TWITTER_API_KEY')
        self.twitter_api_secret = os.getenv('TWITTER_API_SECRET')
        self.twitter_access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.twitter_access_secret = os.getenv('TWITTER_ACCESS_SECRET')
        self.twitter_bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        # Telegram credentials
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # Coinbase Markets X account
        self.coinbase_markets_handle = "CoinbaseMarkets"
        self.coinbase_markets_id = "1474814192166645761"  # Coinbase Markets verified account ID
        
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
        
    async def search_listings(self):
        """Search for listing announcements from Coinbase Markets"""
        try:
            logger.info("Searching for Coinbase Markets listing announcements...")
            
            # Query recent tweets from Coinbase Markets
            # Search for tweets containing listing-related keywords
            query = f"from:{self.coinbase_markets_handle} (listing OR trading OR auction OR available)"
            
            # Get tweets from last hour
            response = self.twitter_client.search_recent_tweets(
                query=query,
                max_results=100,
                tweet_fields=['created_at', 'author_id', 'public_metrics'],
                expansions=['author_id'],
                user_fields=['verified']
            )
            
            if response.data is None:
                logger.warning("No tweets found")
                return
            
            # Process tweets in reverse chronological order (newest first)
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
                    await self._send_telegram_alert(
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
        # Look for uppercase letters in parentheses like (PERP) or (SOLI)
        import re
        matches = re.findall(r'\(([A-Z]+)\)', text)
        if matches:
            return matches[0]
        
        # Fallback: look for common patterns
        words = text.split()
        for word in words:
            if len(word) >= 3 and len(word) <= 6 and word.isupper():
                return word
        
        return "NEW_TOKEN"
    
    async def _send_telegram_alert(self, tweet_text, token_symbol, tweet_url, created_at):
        """Send Telegram notification"""
        try:
            message = f"""
🚀 **COINBASE LISTING DETECTED**

📌 Token: `{token_symbol}`

📝 Announcement:
{tweet_text}

🔗 Tweet: [View on X]({tweet_url})

⏰ Time: {created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
            """
            
            await self.telegram_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Telegram alert sent for {token_symbol}")
            
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}", exc_info=True)
    
    async def monitor_stream(self):
        """Monitor real-time tweets using v2 Streaming API"""
        try:
            logger.info("Starting real-time stream monitoring...")
            
            # Build query for streaming
            query_parts = [
                f"from:{self.coinbase_markets_id}",
                "(listing OR trading OR auction OR available OR \"goes live\" OR \"now live\")"
            ]
            query = " ".join(query_parts)
            
            logger.info(f"Stream query: {query}")
            
            # Create stream rule
            try:
                # Delete existing rules
                rules = self.twitter_client.get_rules()
                if rules.data:
                    rule_ids = [rule.id for rule in rules.data]
                    self.twitter_client.delete_rules(ids=rule_ids)
                
                # Add new rule
                self.twitter_client.add_rules(
                    tweepy.StreamRule(query)
                )
                logger.info("Stream rule added")
            except Exception as e:
                logger.warning(f"Could not update stream rules: {e}")
            
            # Stream tweets
            for response in self.twitter_client.stream(
                tweet_fields=['created_at', 'author_id', 'public_metrics'],
                expansions=['author_id'],
                user_fields=['verified']
            ):
                if response.data:
                    tweet = response.data
                    tweet_id = tweet.id
                    
                    if tweet_id not in self.processed_tweets:
                        if self._is_listing_announcement(tweet.text):
                            logger.info(f"🎯 Stream: Found listing - {tweet.text[:80]}")
                            
                            token_symbol = self._extract_token_symbol(tweet.text)
                            
                            await self._send_telegram_alert(
                                tweet_text=tweet.text,
                                token_symbol=token_symbol,
                                tweet_url=f"https://x.com/{self.coinbase_markets_handle}/status/{tweet_id}",
                                created_at=tweet.created_at
                            )
                            
                            self.processed_tweets.add(tweet_id)
        
        except Exception as e:
            logger.error(f"Error in stream monitoring: {e}", exc_info=True)
            # Restart after 30 seconds
            await asyncio.sleep(30)
    
    async def run(self):
        """Main loop: combine polling and streaming"""
        logger.info("🤖 Coinbase Listing Bot started!")
        
        # Poll every 30 seconds for announcements
        while True:
            try:
                await self.search_listings()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait longer on error


async def main():
    tracker = CoinbaseListingTracker()
    
    # Run polling loop
    await tracker.run()


if __name__ == "__main__":
    asyncio.run(main())
