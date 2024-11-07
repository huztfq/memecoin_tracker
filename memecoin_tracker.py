import os
import tweepy
import pandas as pd
from datetime import datetime
import time
from tabulate import tabulate
import re

# Load Twitter API credentials from environment variables with detailed logging
print("Starting Memecoin Tracker...")

# Check for missing environment variables and log errors if any are missing
bearer_token = os.getenv('TWITTER_BEARER_TOKEN')

missing_vars = []
if not bearer_token:
    missing_vars.append("TWITTER_BEARER_TOKEN")

if missing_vars:
    print(f"Error: Missing environment variables: {', '.join(missing_vars)}")
    print("Please set these variables and restart the script.")
    exit(1)

print("All required environment variables are set.")

# Authentication function with retries
def authenticate_twitter(retries=3):
    for attempt in range(1, retries + 1):
        try:
            print(f"Attempting to authenticate with Twitter API (Attempt {attempt} of {retries})...")
            client = tweepy.Client(
                bearer_token=bearer_token,
                wait_on_rate_limit=True
            )
            client.get_user(username='TwitterDev')  # Simple request to verify authentication
            print("Successfully authenticated with Twitter API.")
            return client
        except Exception as e:
            print(f"Error authenticating with Twitter API: {e}")
            if attempt < retries:
                print("Retrying authentication...")
                time.sleep(2)  # Wait before retrying
            else:
                print("Failed to authenticate with Twitter API after multiple attempts.")
                exit(1)

# Initialize Twitter Client
client = authenticate_twitter()

# Initialize a DataFrame to store memecoin mentions
mentions_df = pd.DataFrame(columns=["symbol", "first_mention", "mention_count", "growth_percentage"])
print("Data structure for tracking mentions initialized.")

def track_memecoins():
    """Function to track memecoins' cashtags ($) dynamically."""
    print("Starting memecoin tracking...")
    try:
        # Define the search query without using '$' to avoid 'cashtag' operator issues
        query = 'memecoin -is:retweet lang:en'  # Adjust language and exclude retweets as needed

        print(f"Using query: {query}")

        # Fetch recent tweets matching the query
        tweets = client.search_recent_tweets(
            query=query,
            tweet_fields=['entities', 'created_at', 'lang'],
            expansions=None,
            max_results=100
        )

        if tweets.data:
            new_mentions = {}
            # Regex pattern to match symbols starting with $
            symbol_pattern = re.compile(r'\$([A-Za-z]{2,})')  # Matches $BTC, $DOGE, etc.

            for tweet in tweets.data:
                symbols = set()

                # Extract $ symbols from tweet text using regex
                symbols_in_text = set(match.group(1).upper() for match in symbol_pattern.finditer(tweet.text))
                symbols = symbols_in_text

                # Validate and filter symbols
                for symbol in symbols:
                    # Basic validation: symbol should be at least 2 characters long
                    if len(symbol) < 2:
                        continue
                    # Optionally, add more exclusion rules or validation here
                    if symbol in ['MEME', 'MEMECOIN']:  # Example filters
                        continue

                    if symbol in new_mentions:
                        new_mentions[symbol] += 1
                    else:
                        new_mentions[symbol] = 1

            if new_mentions:
                current_time = datetime.now()
                for symbol, count in new_mentions.items():
                    symbol_with_dollar = f"${symbol}"
                    if symbol_with_dollar not in mentions_df['symbol'].values:
                        # New symbol, add to DataFrame
                        mentions_df.loc[len(mentions_df)] = [symbol_with_dollar, current_time, count, 0.0]
                        print(f"Added new symbol {symbol_with_dollar}: count = {count}, growth = 0.00%")
                    else:
                        # Existing symbol, update counts and calculate growth
                        row_index = mentions_df.index[mentions_df['symbol'] == symbol_with_dollar][0]
                        previous_count = mentions_df.at[row_index, 'mention_count']
                        mentions_df.at[row_index, 'mention_count'] += count
                        new_count = mentions_df.at[row_index, 'mention_count']

                        if previous_count > 0:
                            growth = ((new_count - previous_count) / previous_count) * 100
                        else:
                            growth = 0.0

                        mentions_df.at[row_index, 'growth_percentage'] = growth
                        print(f"Updated {symbol_with_dollar}: count = {new_count}, growth = {growth:.2f}%")
            else:
                print("No relevant memecoin mentions found in the tweets.")
        else:
            print("No tweets found for the query.")
    except Exception as e:
        print(f"Error during memecoin tracking: {e}")

# Main function with retry logic and continuous monitoring
def main():
    print("Starting main monitoring loop...")
    retries = 3
    attempts = 0
    while attempts < retries:
        try:
            while True:
                track_memecoins()
                print("\nCurrent Memecoin Tracking Data:")
                if not mentions_df.empty:
                    print(tabulate(mentions_df, headers='keys', tablefmt='pretty', showindex=False))
                else:
                    print("No data to display.")
                # Optional: Save data periodically
                mentions_df.to_csv('memecoin_mentions.csv', index=False)
                time.sleep(60)  # Adjust delay as needed
        except Exception as e:
            attempts += 1
            print(f"Error in main loop: {e}")
            if attempts < retries:
                print("Retrying main loop...")
                time.sleep(5)
            else:
                print("Max retries reached in main loop. Exiting.")
                exit(1)

if __name__ == "__main__":
    main()
