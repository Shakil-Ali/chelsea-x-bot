import os
import tweepy

def get_lineup():
    return (
        "🔵 Chelsea Starting XI vs Arsenal:\n"
        "Petrovic, Gusto, Disasi, Silva, Cucurella\n"
        "Caicedo, Enzo, Gallagher\n"
        "Palmer, Jackson, Mudryk\n\n"
        "#CFC #Chelsea"
    )

def tweet_lineup():
    bearer_token = os.getenv("BEARER_TOKEN")

    client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=os.getenv("API_KEY"),
        consumer_secret=os.getenv("API_SECRET"),
        access_token=os.getenv("ACCESS_TOKEN"),
        access_token_secret=os.getenv("ACCESS_SECRET")
    )

    response = client.create_tweet(text=get_lineup())
    print("✅ Tweeted:", response)

if __name__ == "__main__":
    tweet_lineup()
