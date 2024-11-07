import os
import sys
import requests
import logging
import pandas as pd
import time
import tweepy
from datetime import datetime
import re
import threading
from flask import Flask
from collections import defaultdict

# Configure logging to output to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("memecoin_tracker.log"),
        logging.StreamHandler(sys.stderr)
    ]
)

# Constants
TOKEN_PROFILES_URL = "https://api.dexscreener.com/token-profiles/latest/v1"
PAIRS_BY_TOKENS_URL = "https://api.dexscreener.com/latest/dex/tokens/{}"
PAIRS_BATCH_SIZE = 1000
UPDATE_INTERVAL = 180
TWITTER_UPDATE_INTERVAL = 180
TWITTER_QUERY_MAX_LENGTH = 500  # Adjusted to be under Twitter API query length limit

# Twitter API Credentials
bearer_token = os.getenv('TWITTER_BEARER_TOKEN')

if not bearer_token:
    logging.error("TWITTER_BEARER_TOKEN environment variable not set.")
    sys.exit(1)

# Authentication function for Twitter API
def authenticate_twitter():
    try:
        logging.info("Attempting to authenticate with Twitter API...")
        client = tweepy.Client(
            bearer_token=bearer_token,
            wait_on_rate_limit=True
        )
        # Simple request to verify authentication
        client.get_user(username='TwitterDev')
        logging.info("Successfully authenticated with Twitter API.")
        return client
    except Exception as e:
        logging.error(f"Error authenticating with Twitter API: {e}")
        sys.exit(1)

# Initialize Twitter Client
twitter_client = authenticate_twitter()

# Function to get latest token profiles
def get_latest_token_profiles():
    url = TOKEN_PROFILES_URL
    headers = {
        "Accept": "application/json"
    }

    try:
        logging.info("Attempting to fetch latest token profiles from DexScreener...")
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            logging.info("Successfully fetched token profiles from DexScreener.")
            return data if isinstance(data, list) else []
        else:
            logging.error(f"Request failed with status code {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while making the request to DexScreener: {e}")
        return []

# Function to get token details
def get_token_details(token_addresses):
    token_details = {}
    for i in range(0, len(token_addresses), PAIRS_BATCH_SIZE):
        batch = token_addresses[i:i + PAIRS_BATCH_SIZE]
        joined_addresses = ",".join(batch)
        url = PAIRS_BY_TOKENS_URL.format(joined_addresses)
        headers = {
            "Accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'pairs' in data and isinstance(data['pairs'], list):
                    for pair in data['pairs']:
                        base_token = pair.get('baseToken', {})
                        if base_token.get('address') in batch:
                            token_address = base_token.get('address')
                            token_details[token_address] = {
                                'name': base_token.get('name'),
                                'symbol': base_token.get('symbol')
                            }
                logging.info("Successfully fetched token details for current batch.")
            else:
                logging.error(f"Request failed with status code {response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"An error occurred while making the request: {e}")

    return token_details

# Function to fetch token profiles
def fetch_token_profiles():
    token_profiles = get_latest_token_profiles()
    if not token_profiles:
        logging.error("No token profiles fetched. Skipping this iteration.")
        return pd.DataFrame()

    token_addresses = list({profile.get('tokenAddress') for profile in token_profiles if profile.get('tokenAddress')})
    token_details = get_token_details(token_addresses)

    # Prepare the data for the table
    table_data = []
    for profile in token_profiles:
        token_address = profile.get('tokenAddress')
        name = token_details.get(token_address, {}).get('name', 'N/A')
        symbol = token_details.get(token_address, {}).get('symbol', 'N/A')
        table_data.append({
            'Token Address': token_address,
            'Token Name': name,
            'Token Symbol': symbol
        })

    # Convert to DataFrame for better tabular representation
    df = pd.DataFrame(table_data)

    # Return the DataFrame
    return df

# Initialize the mentions DataFrame with all tokens
def initialize_mentions_df(token_profiles_df):
    mentions_data = []
    for index, row in token_profiles_df.iterrows():
        mentions_data.append({
            'Token Address': row['Token Address'],
            'Token Name': row['Token Name'],
            'Token Symbol': row['Token Symbol'],
            'First Mention': None,
            'Mention Count': 0,
            'Growth Percentage': 0.0
        })
    mentions_df = pd.DataFrame(mentions_data)
    return mentions_df

# Global mentions DataFrame and lock
mentions_df = pd.DataFrame()
lock = threading.Lock()  # Thread lock for safe access to mentions_df

# Create Flask app
app = Flask(__name__)

# Route to display the DataFrame as an HTML table
@app.route('/')
def show_table():
    with lock:
        if mentions_df.empty:
            return "No data available"
        else:
            # Filter out tokens with Mention Count > 0
            filtered_df = mentions_df[mentions_df['Mention Count'] > 0]
            # Sort the DataFrame by 'Mention Count' in descending order
            sorted_df = filtered_df.sort_values(by='Mention Count', ascending=False)
            if sorted_df.empty:
                return "No tokens have been mentioned yet."
            # Convert the DataFrame to HTML
            table_html = sorted_df.to_html(
                index=False,
                columns=[
                    'Token Name',
                    'Token Symbol',
                    'Token Address',
                    'First Mention',
                    'Mention Count',
                    'Growth Percentage'
                ],
                justify='left',
                classes='table table-striped'
            )
            # Return the HTML with basic styling
            return f"""
            <html>
            <head>
                <title>Memecoin Tracker</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 20px;
                    }}
                    .table {{
                        width: 100%;
                        border-collapse: collapse;
                    }}
                    .table th, .table td {{
                        border: 1px solid #dddddd;
                        text-align: left;
                        padding: 8px;
                    }}
                    .table th {{
                        background-color: #f2f2f2;
                    }}
                </style>
            </head>
            <body>
                <h1>Memecoin Tracker</h1>
                {table_html}
            </body>
            </html>
            """

# Function to track memecoins
def track_memecoins(token_info):
    """Function to track memecoins' mentions dynamically."""
    global mentions_df
    logging.info("Starting memecoin tracking...")
    try:
        # Build the search queries
        max_query_length = TWITTER_QUERY_MAX_LENGTH
        FIXED_QUERY_PARTS = ' -is:retweet lang:en'
        queries = []
        current_query = ''
        for token in token_info:
            symbol = token['symbol']
            name = token['name']
            # Prepare query parts
            query_parts = []
            # Add cashtag if symbol is valid
            if re.match(r'^[A-Z0-9]{1,15}$', symbol):
                cashtag = f'"${symbol}"'  # Cashtag
                query_parts.append(cashtag)
            # Add symbol as a word
            if re.match(r'^[A-Z0-9]{1,15}$', symbol):
                symbol_query = f'"{symbol}"'
                query_parts.append(symbol_query)
            # Add token name if it's not a common word
            if name and name.lower() not in ['the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'they', 'will']:
                name_query = f'"{name}"'
                query_parts.append(name_query)
            # Combine query parts with OR
            token_query = ' OR '.join(query_parts)
            # Enclose token query in parentheses
            token_query = f'({token_query})'
            # Build up the query batches
            if current_query:
                potential_query = f'{current_query} OR {token_query}'
            else:
                potential_query = token_query
            # Compute the total query length including fixed parts
            total_query = f'({potential_query}){FIXED_QUERY_PARTS}'
            if len(total_query) > max_query_length:
                if current_query:
                    # Append current query to queries
                    queries.append(current_query)
                # Start new current_query with token_query
                current_query = token_query
                # Check if token_query itself exceeds the limit
                total_token_query = f'({token_query}){FIXED_QUERY_PARTS}'
                if len(total_token_query) > max_query_length:
                    logging.warning(f"Token query for {symbol} is too long and will be skipped.")
                    current_query = ''
                    continue
            else:
                current_query = potential_query
        # After loop, append any remaining current_query
        if current_query:
            queries.append(current_query)

        # Now, for each query batch, search tweets
        for query_batch in queries:
            # Build the final query
            query = f'({query_batch}){FIXED_QUERY_PARTS}'
            logging.info(f"Using query: {query}")
            logging.debug(f"Final query length: {len(query)}")

            # Fetch recent tweets matching the query
            tweets = twitter_client.search_recent_tweets(
                query=query,
                tweet_fields=['entities', 'created_at', 'lang'],
                max_results=100
            )

            if tweets.data:
                logging.info(f"Fetched {len(tweets.data)} tweets.")
                new_mentions = defaultdict(int)
                for tweet in tweets.data:
                    text = tweet.text.upper()
                    for token in token_info:
                        symbol = token['symbol'].upper()
                        name = token['name'].upper()
                        symbol_regex = re.compile(r'\b{}\b'.format(re.escape(symbol)))
                        name_regex = re.compile(r'\b{}\b'.format(re.escape(name)))
                        cashtag_regex = re.compile(r'\${}'.format(re.escape(symbol)))

                        if cashtag_regex.search(text) or symbol_regex.search(text) or name_regex.search(text):
                            key = token['symbol']
                            new_mentions[key] += 1

                if new_mentions:
                    current_time = datetime.now()
                    with lock:
                        for symbol, count in new_mentions.items():
                            # Find the row index for this symbol
                            row_indices = mentions_df.index[mentions_df['Token Symbol'].str.upper() == symbol.upper()].tolist()
                            if row_indices:
                                row_index = row_indices[0]
                                previous_count = mentions_df.at[row_index, 'Mention Count']
                                mentions_df.at[row_index, 'Mention Count'] += count
                                new_count = mentions_df.at[row_index, 'Mention Count']

                                # Update 'First Mention' if it's None
                                if pd.isna(mentions_df.at[row_index, 'First Mention']):
                                    mentions_df.at[row_index, 'First Mention'] = current_time

                                if previous_count > 0:
                                    growth = ((new_count - previous_count) / previous_count) * 100
                                else:
                                    growth = 0.0

                                mentions_df.at[row_index, 'Growth Percentage'] = growth
                                logging.info(f"Updated {symbol}: count = {new_count}, growth = {growth:.2f}%")
                            else:
                                # Should not happen since all tokens are initialized
                                logging.warning(f"Symbol {symbol} not found in mentions_df.")
                else:
                    logging.info("No relevant memecoin mentions found in the tweets.")
            else:
                logging.info("No tweets found for the query.")
    except Exception as e:
        logging.error(f"Error during memecoin tracking: {e}")

def data_updater():
    """Function to continuously update data in the background."""
    global mentions_df
    while True:
        # Fetch token profiles and get token symbols
        token_profiles_df = fetch_token_profiles()
        if token_profiles_df.empty:
            logging.error("No token profiles fetched. Skipping this iteration.")
            time.sleep(UPDATE_INTERVAL)
            continue

        # Initialize mentions_df with all tokens if it's empty
        with lock:
            if mentions_df.empty:
                mentions_df = initialize_mentions_df(token_profiles_df)

        # Build a list of token information
        token_info = []
        for index, row in token_profiles_df.iterrows():
            symbol = row['Token Symbol']
            address = row['Token Address']
            name = row['Token Name']
            symbol_clean = symbol.strip().replace('$', '').upper()
            # Validate symbol: must be 1-15 alphanumeric characters, no spaces, no special chars
            if symbol_clean != '' and symbol_clean != 'N/A':
                if re.match(r'^[A-Z0-9]{1,15}$', symbol_clean):
                    token_info.append({
                        'symbol': symbol_clean,
                        'name': name.strip(),
                        'address': address
                    })
                else:
                    logging.warning(f"Invalid symbol '{symbol_clean}' skipped.")

        if not token_info:
            logging.warning("No valid token symbols to track. Skipping this iteration.")
            time.sleep(UPDATE_INTERVAL)
            continue

        # Log the symbols
        logging.info(f"Token symbols to track: {[token['symbol'] for token in token_info]}")

        # Track memecoin mentions
        track_memecoins(token_info)

        # Wait before the next update
        logging.info(f"Waiting for {TWITTER_UPDATE_INTERVAL} seconds before the next update.")
        time.sleep(TWITTER_UPDATE_INTERVAL)

def main():
    logging.info("Starting DexScreener Token Profiles Monitor and Memecoin Tracker.")
    try:
        # Ensure both connections are established before starting the main loop
        logging.info("Establishing connection to DexScreener...")
        token_profiles_df = fetch_token_profiles()
        if token_profiles_df.empty:
            logging.error("Failed to fetch token profiles from DexScreener. Exiting.")
            sys.exit(1)
        else:
            logging.info("Successfully connected to DexScreener.")

        # Initialize mentions_df with all tokens
        global mentions_df
        mentions_df = initialize_mentions_df(token_profiles_df)

        # Twitter authentication is already done during initialization
        logging.info("Connections established. Starting the data updater thread.")

        # Start the data updater in a separate thread
        updater_thread = threading.Thread(target=data_updater)
        updater_thread.daemon = True  # Allows program to exit even if thread is running
        updater_thread.start()

        # Start the Flask app
        app.run(debug=False)
    except KeyboardInterrupt:
        logging.info("Script terminated by user.")

if __name__ == "__main__":
    main()
