import os
import json
import requests
from datetime import datetime, timezone
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
TEAM_ID = 61  # Chelsea
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
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {
            "match_id": None,
            "lineup_posted": False,
            "goals_posted": [],
            "subs_posted": [],
            "final_score_posted": False
        }


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_today_match():
    """Get Chelsea match for today from all competitions"""
    today = datetime.now(timezone.utc).date()
    
    # Get matches for today and tomorrow (timezone buffer)
    tomorrow = datetime.now(timezone.utc).date().replace(day=today.day + 1) if today.day < 28 else today
    url = f"https://api.football-data.org/v4/teams/{TEAM_ID}/matches"
    params = {
        'dateFrom': today.isoformat(),
        'dateTo': tomorrow.isoformat()  # Include tomorrow for timezone safety
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"API Response: {data}")  # Debug logging
        
        matches = data.get("matches", [])
        if matches:
            # Return the first match found for today
            match = matches[0]
            print(f"Found match: {match['homeTeam']['name']} vs {match['awayTeam']['name']} at {match['utcDate']}")
            return match
        else:
            print(f"No matches found for today ({today})")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching matches: {e}")
        return None


def get_match_details(match_id):
    """Get detailed match information including lineups and events"""
    url = f"https://api.football-data.org/v4/matches/{match_id}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        print(f"Match details status: {data.get('status', 'Unknown')}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching match details: {e}")
        return None


def post_lineup(match_details, state):
    """Post starting lineup when available"""
    if not match_details or state["lineup_posted"]:
        return
        
    # Check if lineups are available
    lineups = match_details.get("lineups", [])
    if not lineups:
        print("No lineups available yet")
        return
    
    # Find Chelsea's lineup
    chelsea_lineup = None
    for lineup in lineups:
        if lineup["team"]["id"] == TEAM_ID:
            chelsea_lineup = lineup
            break
    
    if chelsea_lineup and chelsea_lineup.get("startXI"):
        try:
            players = [player["name"] for player in chelsea_lineup["startXI"]]
            formation = chelsea_lineup.get("formation", "Unknown")
            
            tweet = f"🔵 Chelsea Starting XI ({formation}):\n\n" + "\n".join([f"• {player}" for player in players])
            
            if len(tweet) > 280:  # Twitter character limit
                tweet = f"🔵 Chelsea Starting XI:\n\n" + "\n".join([f"• {player}" for player in players[:11]])
            
            api.update_status(tweet)
            print("✅ Lineup tweeted.")
            state["lineup_posted"] = True
        except Exception as e:
            print(f"Error posting lineup: {e}")


def post_goals(match_details, state):
    """Post goals as they happen"""
    if not match_details:
        return
        
    # Get all goal events
    events = match_details.get("events", [])
    goals = [e for e in events if e.get("type") == "GOAL"]
    
    for goal in goals:
        goal_id = goal.get("id")
        if goal_id and goal_id not in state["goals_posted"]:
            try:
                team_name = goal["team"]["name"]
                scorer = goal["player"]["name"]
                minute = goal.get("minute", "?")
                
                # Check if it's Chelsea or opponent
                emoji = "⚽️🔵" if goal["team"]["id"] == TEAM_ID else "⚽️"
                
                tweet = f"{emoji} GOAL!\n{team_name}: {scorer} ({minute}')"
                
                api.update_status(tweet)
                print(f"✅ Goal tweeted: {scorer}")
                state["goals_posted"].append(goal_id)
            except Exception as e:
                print(f"Error posting goal: {e}")


def post_subs(match_details, state):
    """Post substitutions"""
    if not match_details:
        return
        
    events = match_details.get("events", [])
    subs = [e for e in events if e.get("type") == "SUBSTITUTION"]
    
    for sub in subs:
        sub_id = sub.get("id")
        if sub_id and sub_id not in state["subs_posted"]:
            try:
                # Only post Chelsea substitutions
                if sub["team"]["id"] == TEAM_ID:
                    player_in = sub["player"]["name"]
                    player_out = sub.get("assist", {}).get("name", "Unknown")
                    minute = sub.get("minute", "?")
                    
                    tweet = f"🔁 Chelsea Substitution ({minute}'):\n⬅️ {player_out}\n➡️ {player_in}"
                    
                    api.update_status(tweet)
                    print(f"✅ Substitution tweeted: {player_in} for {player_out}")
                
                state["subs_posted"].append(sub_id)
            except Exception as e:
                print(f"Error posting substitution: {e}")


def post_final_score(match_details, state):
    """Post final score when match is finished"""
    if not match_details or state["final_score_posted"]:
        return
        
    if match_details.get("status") == "FINISHED":
        try:
            score = match_details.get("score", {}).get("fullTime", {})
            home_team = match_details["homeTeam"]["name"]
            away_team = match_details["awayTeam"]["name"]
            home_score = score.get("home", 0)
            away_score = score.get("away", 0)
            
            # Determine result for Chelsea
            if match_details["homeTeam"]["id"] == TEAM_ID:
                chelsea_score = home_score
                opponent_score = away_score
                opponent = away_team
            else:
                chelsea_score = away_score
                opponent_score = home_score
                opponent = home_team
            
            if chelsea_score > opponent_score:
                result_emoji = "🎉✅"
            elif chelsea_score < opponent_score:
                result_emoji = "😞❌"
            else:
                result_emoji = "🤝"
            
            tweet = f"{result_emoji} FULL TIME\n\n{home_team} {home_score} - {away_score} {away_team}\n\n#CFC #Chelsea"
            
            api.update_status(tweet)
            print("✅ Final score tweeted.")
            state["final_score_posted"] = True
        except Exception as e:
            print(f"Error posting final score: {e}")


def main():
    print(f"🤖 Chelsea Bot running at {datetime.now(timezone.utc)}")
    
    # Load previous state
    state = load_state()
    
    # Get today's match
    match = get_today_match()
    
    if not match:
        print("📅 No Chelsea match today.")
        return
    
    match_id = match["id"]
    match_status = match.get("status", "Unknown")
    
    print(f"📊 Match found: {match['homeTeam']['name']} vs {match['awayTeam']['name']}")
    print(f"📊 Match status: {match_status}")
    print(f"📊 Match time: {match['utcDate']}")
    
    # Reset state if this is a new match
    if state["match_id"] != match_id:
        print("🔄 New match detected, resetting state")
        state = {
            "match_id": match_id,
            "lineup_posted": False,
            "goals_posted": [],
            "subs_posted": [],
            "final_score_posted": False
        }
    
    # Get detailed match information
    match_details = get_match_details(match_id)
    
    if not match_details:
        print("❌ Could not fetch match details")
        return
    
    # Post updates based on match status
    # Try to post lineup even for SCHEDULED matches (in case lineups are available early)
    if match_status in ["SCHEDULED", "TIMED", "IN_PLAY", "PAUSED", "FINISHED"]:
        post_lineup(match_details, state)
    
    # Only post live updates for active/finished matches
    if match_status in ["IN_PLAY", "PAUSED", "FINISHED"]:
        post_goals(match_details, state)
        post_subs(match_details, state)
    
    if match_status == "FINISHED":
        post_final_score(match_details, state)
    
    # Save state
    save_state(state)
    print("✅ Bot execution completed")


if __name__ == "__main__":
    main()
