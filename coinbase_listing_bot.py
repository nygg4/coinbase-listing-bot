import time
import logging
import os
import re
from telegram import Bot
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CoinbaseListingTracker:
    def __init__(self):
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.nitter_urls = ["https://nitter.net/CoinbaseMarkets", "https://nitter.1d4.us/CoinbaseMarkets"]
        self.processed_tweets = set()
        self.listing_keywords = [
            "PRE listing",
            "trading goes live",
            "now available",
            "auction",
            "spot trading",
            "will go live",
            "available on coinbase",
            "is now live",
            "based one",
            "limit-only mode",
            "enter auction mode",
            "crosses mid",
            "trading begins",
            "listing announcement",
            "assets added",
            "contract address",
            "coinbase exchange",
            "newly added",
            "support for"
        ]
        self.telegram_bot = Bot(token=self.telegram_token)
    
    def get_tweets_from_nitter(self):
        try:
            logger.info("Fetching tweets from Nitter...")
            for nitter_url in self.nitter_urls:
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    response = requests.get(nitter_url, headers=headers, timeout=10)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    tweets = soup.find_all('div', class_='tweet')
                    if tweets:
                        logger.info(f"Found {len(tweets)} tweets")
                        for tweet in tweets:
                            text_elem = tweet.find('p', class_='tweet-text')
                            if not text_elem:
                                continue
                            tweet_text = text_elem.get_text()
                            if self._is_listing_announcement(tweet_text):
                                logger.info(f"Found listing: {tweet_text[:80]}")
                                token = self._extract_token_symbol(tweet_text)
                                self._send_alert(tweet_text, token)
                    return True
                except:
                    continue
        except Exception as e:
            logger.error(f"Error: {e}")
    
    def _is_listing_announcement(self, text):
        return any(kw.lower() in text.lower() for kw in self.listing_keywords)
    
    def _extract_token_symbol(self, text):
        matches = re.findall(r'\(([A-Z]+)\)', text)
        return matches[0] if matches else "NEW"
    
    def _send_alert(self, text, symbol):
        try:
            msg = f"COINBASE LISTING\n\nToken: {symbol}\n\nAnnouncement:\n{text}"
            self.telegram_bot.send_message(chat_id=self.telegram_chat_id, text=msg)
            logger.info(f"Alert sent for {symbol}")
        except Exception as e:
            logger.error(f"Error: {e}")
    
    def run(self):
        logger.info("Bot started!")
        while True:
            try:
                self.get_tweets_from_nitter()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    tracker = CoinbaseListingTracker()
    tracker.run()
