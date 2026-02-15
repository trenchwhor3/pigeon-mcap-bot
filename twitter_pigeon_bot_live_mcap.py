"""
Twitter Bot - Dynamic Pigeon Market Cap Tracker
Posts daily updates with LIVE market cap data from DexScreener
"""

import tweepy
import schedule
import time
from datetime import datetime
import json
import os
import requests
from dotenv import load_dotenv

class PigeonMarketCapBot:
    def __init__(self, api_key, api_secret, access_token, access_token_secret, bearer_token):
        """Initialize Twitter API connection"""
        # Twitter API v2 Client
        self.client = tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        # Configuration
        self.target_mcap = 941_000_000  # 941M
        self.token_address = "4fSWEw2wbYEUCcMtitzmeGUfqinoafXxkhqZrA9Gpump"  # Pigeon token
        self.dexscreener_url = f"https://api.dexscreener.com/latest/dex/tokens/{self.token_address}"
        self.data_file = "bot_data.json"
        self.load_data()
    
    def load_data(self):
        """Load bot data from file"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {
                'day_count': 0,
                'start_date': datetime.now().strftime('%Y-%m-%d'),
                'last_post_date': None,
                'reached_target': False
            }
            self.save_data()
    
    def save_data(self):
        """Save bot data to file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def get_current_mcap(self):
        """
        Fetch current market cap from DexScreener API
        Returns: dict with mcap info or None if error
        """
        try:
            response = requests.get(self.dexscreener_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data and 'pairs' in data and len(data['pairs']) > 0:
                pair = data['pairs'][0]  # Get first pair (most liquid)
                
                # Extract market cap (use fdv - fully diluted valuation)
                mcap_str = pair.get('fdv', 0)
                price = pair.get('priceUsd', '0')
                liquidity = pair.get('liquidity', {}).get('usd', 0)
                
                return {
                    'mcap': float(mcap_str) if mcap_str else 0,
                    'price': float(price) if price else 0,
                    'liquidity': float(liquidity) if liquidity else 0,
                    'success': True
                }
            
            return None
            
        except Exception as e:
            print(f"⚠️  Error fetching market cap: {str(e)}")
            return None
    
    def format_number(self, num):
        """Format large numbers with K, M, B suffixes"""
        if num >= 1_000_000_000:
            return f"${num/1_000_000_000:.2f}B"
        elif num >= 1_000_000:
            return f"${num/1_000_000:.2f}M"
        elif num >= 1_000:
            return f"${num/1_000:.2f}K"
        else:
            return f"${num:.2f}"
    
    def post_daily_update(self):
        """Post the daily market cap update with live data"""
        try:
            # Check if we already posted today
            today = datetime.now().strftime('%Y-%m-%d')
            if self.data.get('last_post_date') == today:
                print(f"⏭️  Already posted today ({today}). Skipping.")
                return
            
            # Fetch current market cap
            mcap_data = self.get_current_mcap()
            
            if mcap_data and mcap_data['success']:
                current_mcap = mcap_data['mcap']
                current_mcap_formatted = self.format_number(current_mcap)
                
                # Check if we've reached target
                if current_mcap >= self.target_mcap and not self.data.get('reached_target'):
                    # Special tweet for reaching target!
                    tweet_text = f"🎉 PIGEON HAS REACHED 941M MCAP! 🚀\n\nCurrent Market Cap: {current_mcap_formatted}\n\nIt took {self.data['day_count']} days! LFG! 🐦💎"
                    self.data['reached_target'] = True
                elif current_mcap >= self.target_mcap:
                    # Already above target
                    tweet_text = f"Day {self.data['day_count']} - Pigeon holding strong above 941M! 💪\n\nCurrent Market Cap: {current_mcap_formatted}"
                else:
                    # Still under target
                    self.data['day_count'] += 1
                    remaining = self.target_mcap - current_mcap
                    remaining_formatted = self.format_number(remaining)
                    
                    tweet_text = f"Day {self.data['day_count']} of posting pigeon under 941M mcap\n\nCurrent: {current_mcap_formatted}\nTarget: $941M\nTo go: {remaining_formatted} 🐦"
            else:
                # Fallback if API fails
                self.data['day_count'] += 1
                tweet_text = f"Day {self.data['day_count']} of posting pigeon under 941M mcap 🐦"
                print("⚠️  Using fallback tweet (API unavailable)")
            
            # Post the tweet
            response = self.client.create_tweet(text=tweet_text)
            
            # Update last post date
            self.data['last_post_date'] = today
            self.save_data()
            
            print(f"✅ Posted: {tweet_text}")
            print(f"📅 Date: {today}")
            print(f"🆔 Tweet ID: {response.data['id']}")
            
            if mcap_data:
                print(f"💰 Current Price: ${mcap_data['price']:.6f}")
                print(f"💧 Liquidity: {self.format_number(mcap_data['liquidity'])}")
            
        except tweepy.TweepyException as e:
            print(f"❌ Twitter API Error: {str(e)}")
        except Exception as e:
            print(f"❌ Unexpected Error: {str(e)}")
    
    def run_once(self):
        """Run the bot once (for testing)"""
        print("🔄 Running single post...")
        
        # First, show current market cap
        mcap_data = self.get_current_mcap()
        if mcap_data:
            print(f"\n📊 Current Pigeon Stats:")
            print(f"   Market Cap: {self.format_number(mcap_data['mcap'])}")
            print(f"   Price: ${mcap_data['price']:.6f}")
            print(f"   Liquidity: {self.format_number(mcap_data['liquidity'])}")
            print(f"   Target: $941M")
            print(f"   Distance to target: {self.format_number(self.target_mcap - mcap_data['mcap'])}\n")
        
        self.post_daily_update()
    
    def run_scheduled(self, post_time="09:00"):
        """Run the bot on a daily schedule"""
        # Schedule daily post
        schedule.every().day.at(post_time).do(self.post_daily_update)
        
        print("🤖 Bot started!")
        print(f"📊 Current day count: {self.data['day_count']}")
        print(f"📅 Last post: {self.data.get('last_post_date', 'Never')}")
        print(f"⏰ Next post scheduled for: {post_time} daily")
        print(f"🎯 Target: $941M mcap")
        
        # Show current status
        mcap_data = self.get_current_mcap()
        if mcap_data:
            print(f"💰 Current Market Cap: {self.format_number(mcap_data['mcap'])}")
            if mcap_data['mcap'] < self.target_mcap:
                remaining = self.target_mcap - mcap_data['mcap']
                print(f"📈 Distance to target: {self.format_number(remaining)}")
            else:
                print(f"🎉 Already above target!")
        
        print("\nPress Ctrl+C to stop\n")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\n\n👋 Bot stopped by user")


def main():
    """Main function to run the bot"""
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get Twitter API Credentials from environment
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
    ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
    BEARER_TOKEN = os.getenv("BEARER_TOKEN")
    
    # Validate credentials
    if not all([API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET, BEARER_TOKEN]):
        print("❌ Error: Missing Twitter API credentials!")
        print("Please set up your .env file with all required credentials.")
        print("See .env.example for template.")
        return
    
    # Initialize bot
    bot = PigeonMarketCapBot(
        api_key=API_KEY,
        api_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET,
        bearer_token=BEARER_TOKEN
    )
    
    # Get mode from environment or default to scheduled
    mode = os.getenv("BOT_MODE", "scheduled")
    post_time = os.getenv("POST_TIME", "09:00")
    
    if mode == "once":
        bot.run_once()
    else:
        bot.run_scheduled(post_time=post_time)


if __name__ == "__main__":
    main()
