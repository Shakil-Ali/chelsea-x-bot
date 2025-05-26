import tweepy
import os

def get_lineup():
    # Replace with real data or web scrape later
    return (
        "🔵 Chelsea Starting XI vs Arsenal:\n"
        "Petrovic, Gusto, Disasi, Silva, Cucurella\n"
        "Caicedo, Enzo, Gallagher\n"
        "Palmer, Jackson, Mudryk\n\n"
        "#CFC #Chelsea"
    )

def tweet_lineup():
    # Get credentials from environment variables
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    access_token = os.getenv("ACCESS_TOKEN")
    access_secret = os.getenv("ACCESS_SECRET")

    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api = tweepy.API(auth)

    lineup = get_lineup()
    api.update_status(lineup)
    print("✅ Tweet posted!")

if __name__ == "__main__":
    tweet_lineup()
