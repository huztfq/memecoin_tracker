Here’s a README file that outlines the setup, installation, and functional overview of your project.

---

# Memecoin Tracker

This Memecoin Tracker monitors real-time mentions of memecoins on Twitter and displays token profile details fetched from the DexScreener API. The application collects and updates token information and Twitter data, and presents it through a web interface.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Installation and Setup](#installation-and-setup)
4. [Running the Application](#running-the-application)
5. [Functional Overview](#functional-overview)
6. [Additional Notes](#additional-notes)

---

## Project Overview

This project is designed to track mentions of specific memecoins on Twitter and obtain real-time token information from the DexScreener API. It authenticates with the Twitter API using Tweepy, retrieves token details, and serves an HTML table that displays mentions, growth, and other relevant data for each token. The data refreshes automatically at regular intervals and can be accessed via a web interface.

---

## Prerequisites

Ensure you have the following before you begin:

- Python 3.7 or higher installed.
- A Twitter Developer Account with a Bearer Token for API access.
- Virtual environment tool (`venv` or `virtualenv`).
- Access to the DexScreener API for fetching token profiles.

---

## Installation and Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd memecoin_tracker
```

### 2. Set Up a Virtual Environment

Create a virtual environment to manage dependencies.

```bash
python3 -m venv memecoin_tracker_env
source memecoin_tracker_env/bin/activate
```

### 3. Install Required Python Packages

Use the `requirements.txt` file to install the necessary dependencies.

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

The application requires the Twitter Bearer Token to connect to the Twitter API. Set the environment variable as follows:

```bash
export TWITTER_BEARER_TOKEN='your_twitter_bearer_token'
```

Or add it to your shell profile (`~/.bashrc` or `~/.zshrc` for example):

```bash
echo "export TWITTER_BEARER_TOKEN='your_twitter_bearer_token'" >> ~/.bashrc
source ~/.bashrc
```

---

## Running the Application

To start the application, run the `final.py` file:

```bash
python final.py
```

The application will automatically:

1. Authenticate with Twitter using the provided Bearer Token.
2. Fetch token profiles from the DexScreener API.
3. Initialize tracking for each token's mentions on Twitter.
4. Start a Flask web server to display the data as an HTML table.

---

## Functional Overview

- **Token Profile Fetching**: Retrieves the latest token profiles from the DexScreener API, storing each token's details.
- **Twitter Mention Tracking**: Tracks mentions of each token (by its symbol) on Twitter, updating the mention count and growth percentage.
- **Data Update Thread**: Runs a background thread to continuously refresh the data from both Twitter and DexScreener at set intervals.
- **Web Interface**: Displays token profiles, mentions, and growth percentages in an HTML table that updates with each data refresh cycle.

---

## Additional Notes

- Logs are saved to `memecoin_tracker.log` for debugging and tracking execution details.
- The tracked data is saved in a CSV file `memecoin_mentions.csv`, which can be used for analysis.
- The Flask web server will run locally on port `5000` by default and can be accessed by navigating to `http://localhost:5000` in your browser. 

