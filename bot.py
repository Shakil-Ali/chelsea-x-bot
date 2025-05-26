import os
import requests
from datetime import datetime
import tweepy

# Twitter Auth
consumer_key = os.getenv("API_KEY")
consumer_secret = os.getenv("API_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_secret = os.getenv("ACCESS_SECRET")

auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_secret)
api = tweepy.API(auth)

# Football Data API
football_api_key = os.getenv("FOOTBALL_API_KEY")
headers = {"X-Auth-Token": football_api_key}
chelsea_team_id = 61

def get_today_match():
    url = f"https://api.football-data.org/v4/teams/{chelsea_team_id}/matches?status=SCHEDULED"
    response = requests.get(url, headers=headers)
    data = response.json()

    today = datetime.now().date()
    for match in data.get("matches", []):
        match_date = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00")).date()
        if match_date == today:
            return match
    return None

def get_match_details(match_id):
    url = f"https://api.football-data.org/v4/matches/{match_id}"
    response = requests.get(url, headers=headers)
    return response.json()

def post_lineup(match_details):
    lineup_info = match_details.get("match", {}).get("lineups", [])
    chelsea_lineup = next((l for l in lineup_info if l["team"]["id"] == chelsea_team_id), None)

    if chelsea_lineup:
        players = [p["name"] for p in chelsea_lineup["startXI"]]
        tweet = "🔵 Chelsea Starting XI:\n" + "\n".join(players)
        api.update_status(tweet)
        print("✅ Lineup tweeted.")
    else:
        print("⏳ Lineup not available yet.")

def post_score(match_details):
    match = match_details["match"]
    if match["status"] == "FINISHED":
        home = match["homeTeam"]["name"]
        away = match["awayTeam"]["name"]
        score = match["score"]["fullTime"]
        tweet = f"📊 Full Time:\n{home} {score['home']} - {score['away']} {away}"
        api.update_status(tweet)
        print("✅ Score tweeted.")
    else:
        print("⏳ Match not finished yet.")

def main():
    match = get_today_match()
    if match:
        match_id = match["id"]
        match_details = get_match_details(match_id)
        post_lineup(match_details)
        post_score(match_details)
    else:
        print("📅 No Chelsea match today.")

if __name__ == "__main__":
    main()
