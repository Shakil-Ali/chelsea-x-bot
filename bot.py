import os
import requests
import tweepy
import json
from datetime import datetime

# Constants
TEAM_ID = 61  # Chelsea FC ID
TODAY = datetime.now().date()
STATE_FILE = "state.json"

# Twitter authentication
api_key = os.getenv("API_KEY")
api_key_secret = os.getenv("API_KEY_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

# Sanity check
if not all([api_key, api_key_secret, access_token, access_token_secret]):
    raise Exception("❌ Missing Twitter API credentials")

# Auth
auth = tweepy.OAuthHandler(api_key, api_key_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

# Verify credentials
try:
    api.verify_credentials()
    print("✅ Twitter Auth OK")
except Exception as e:
    print("❌ Twitter Auth failed:", e)
    exit()

# Load state
try:
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
except FileNotFoundError:
    state = {}

# Football API setup
football_api_key = os.getenv("FOOTBALL_API_KEY")
headers = {"X-Auth-Token": football_api_key}
football_api_url = "https://api.football-data.org/v4/teams/61/matches?status=SCHEDULED"

# Fetch Chelsea's upcoming match
resp = requests.get(football_api_url, headers=headers)
if resp.status_code != 200:
    print("❌ Failed to fetch match info:", resp.text)
    exit()

matches = resp.json().get("matches", [])
today_match = next((m for m in matches if datetime.fromisoformat(m["utcDate"][:-1]).date() == TODAY), None)

if not today_match:
    print("⚠️ No Chelsea match found today.")
    exit()

match_id = today_match["id"]
print("✅ Found today's match ID:", match_id)

# Get detailed match info
details_url = f"https://api.football-data.org/v4/matches/{match_id}"
resp = requests.get(details_url, headers=headers)

if resp.status_code != 200:
    print("❌ Failed to fetch match details:", resp.text)
    exit()

match_details = resp.json()
lineups = match_details.get("lineups", [])
print(f"ℹ️ Lineups data received: {len(lineups)} teams listed")

# Debug: show team IDs
for lineup in lineups:
    print("Lineup team ID:", lineup["team"]["id"])

# Find Chelsea lineup
chelsea_lineup = next((team for team in lineups if team["team"]["id"] == TEAM_ID), None)

if not chelsea_lineup:
    print("⚠️ Chelsea lineup not available yet.")
    exit()

# Check if lineup already posted
if str(match_id) in state and state[str(match_id)].get("lineup_posted"):
    print("✅ Lineup already posted for this match.")
    exit()

# Format and send tweet
players = [player["name"] for player in chelsea_lineup["startXI"]]
tweet = "🔵 Chelsea FC Starting XI:\n\n" + "\n".join(f"• {p}" for p in players)

print("📤 Tweet content:\n", tweet)

try:
    api.update_status(tweet)
    print("✅ Lineup tweet posted.")
except Exception as e:
    print("❌ Failed to post tweet:", e)
    exit()

# Update state
state[str(match_id)] = {"lineup_posted": True}

with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)
