import os, json, requests
from datetime import datetime
import tweepy

# --- Twitter Auth ---
auth = tweepy.OAuth1UserHandler(
    os.getenv("API_KEY"),
    os.getenv("API_SECRET"),
    os.getenv("ACCESS_TOKEN"),
    os.getenv("ACCESS_SECRET")
)
api = tweepy.API(auth)

# --- Constants ---
TEAM_ID = 61  # Chelsea FC
STATE_FILE = "state.json"
headers = {"X-Auth-Token": os.getenv("FOOTBALL_API_KEY")}

def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "match_id": None,
            "lineup_posted": False,
            "goals_posted": [],
            "subs_posted": [],
            "final_score_posted": False
        }
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def get_today_match():
    # Check multiple statuses in case match is live or finished
    statuses = ["SCHEDULED", "TIMED", "IN_PLAY", "PAUSED", "FINISHED"]
    today = datetime.utcnow().date()

    for status in statuses:
        url = f"https://api.football-data.org/v4/teams/{TEAM_ID}/matches?status={status}"
        res = requests.get(url, headers=headers).json()
        for match in res.get("matches", []):
            match_date = datetime.fromisoformat(match["utcDate"].replace("Z", "+00:00")).date()
            if match_date == today:
                return match
    return None

def get_match_details(match_id):
    url = f"https://api.football-data.org/v4/matches/{match_id}"
    return requests.get(url, headers=headers).json()

def post_lineup(match_details, state):
    lineup_data = match_details.get("match", {}).get("lineups", [])
    lineup = next((l for l in lineup_data if l["team"]["id"] == TEAM_ID), None)
    if lineup and not state["lineup_posted"]:
        names = [p["name"] for p in lineup["startXI"]]
        tweet = "🔵 Chelsea Starting XI:\n" + "\n".join(names)
        api.update_status(tweet)
        print("✅ Lineup tweeted.")
        state["lineup_posted"] = True

def post_goals(match_details, state):
    goals = [e for e in match_details["match"].get("events", []) if e["type"] == "GOAL"]
    for goal in goals:
        if goal["id"] not in state["goals_posted"]:
            team = goal["team"]["name"]
            scorer = goal["player"]["name"]
            minute = goal["minute"]
            tweet = f"⚽ {team} Goal!\n{scorer} ({minute}’)"
            api.update_status(tweet)
            print("✅ Goal tweeted.")
            state["goals_posted"].append(goal["id"])

def post_subs(match_details, state):
    subs = [e for e in match_details["match"].get("events", []) if e["type"] == "SUBSTITUTION"]
    for sub in subs:
        if sub["id"] not in state["subs_posted"]:
            team = sub["team"]["name"]
            in_player = sub["player"]["name"]
            out_player = sub.get("assist", {}).get("name", "Unknown")
            minute = sub["minute"]
            tweet = f"🔁 Substitution for {team}:\n⬅ {out_player}\n➡ {in_player} ({minute}’)"
            api.update_status(tweet)
            print("✅ Sub tweeted.")
            state["subs_posted"].append(sub["id"])

def post_final_score(match_details, state):
    if not state["final_score_posted"] and match_details["match"]["status"] == "FINISHED":
        score = match_details["match"]["score"]["fullTime"]
        home = match_details["match"]["homeTeam"]["name"]
        away = match_details["match"]["awayTeam"]["name"]
        tweet = f"📊 Full Time:\n{home} {score['home']} - {score['away']} {away}"
        api.update_status(tweet)
        print("✅ Final score tweeted.")
        state["final_score_posted"] = True

def main():
    state = load_state()
    match = get_today_match()

    if not match:
        print("📅 No Chelsea match today.")
        return

    match_id = match["id"]

    # Reset state if it's a new match
    if state["match_id"] != match_id:
        state = {
            "match_id": match_id,
            "lineup_posted": False,
            "goals_posted": [],
            "subs_posted": [],
            "final_score_posted": False
        }

    match_details = get_match_details(match_id)

    post_lineup(match_details, state)
    post_goals(match_details, state)
    post_subs(match_details, state)
    post_final_score(match_details, state)

    save_state(state)

if __name__ == "__main__":
    main()
