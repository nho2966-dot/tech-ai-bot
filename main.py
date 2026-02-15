import os
import time
import yaml
import random
import feedparser
import tweepy
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import openai
from google import genai  # استخدام google-genai v1.63.0

# تحميل المفاتيح من .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

# إعدادات OpenAI و Gemini
openai.api_key = OPENAI_API_KEY
client_genai = genai.TextGenerationClient(api_key=GEMINI_API_KEY)

# تحميل الإعدادات من YAML
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# إعداد تويتر
auth = tweepy.OAuth1UserHandler(
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
)
twitter = tweepy.API(auth, wait_on_rate_limit=True)

# مراقبة الحسابات الاستراتيجية
monitored_accounts = config.get("monitored_accounts", [])

# RSS feeds
rss_feeds = config.get("sources", {}).get("rss_feeds", [])

# حدود النشر والرد
DAILY_TWEET_LIMIT = 3
DAILY_REPLY_LIMIT = 10

# توقيت النوم
SLEEP_START = config.get("bot", {}).get("sleep_start", 2)
SLEEP_END = config.get("bot", {}).get("sleep_end", 8)

def in_sleep_hours():
    current_hour = time.localtime().tm_hour
    return SLEEP_START <= current_hour < SLEEP_END

# وظائف مساعدة
def get_rss_articles():
    articles = []
    for feed in rss_feeds:
        parsed = feedparser.parse(feed["url"])
        for entry in parsed.entries[:5]:
            articles.append(entry.title + " " + entry.link)
    return articles

def generate_tweet(content, mode="POST_FAST"):
    prompt_template = config["prompts"]["modes"].get(mode, "{content}")
    prompt = prompt_template.format(content=content)
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": config["prompts"]["system_core"]},
                  {"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=200
    )
    return response.choices[0].message.content.strip()

def generate_reply(tweet_content):
    prompt = config["prompts"]["modes"]["REPLY"].format(content=tweet_content)
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": config["prompts"]["system_core"]},
                  {"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=150
    )
    return response.choices[0].message.content.strip()

def post_tweet(text):
    try:
        twitter.update_status(status=text)
        print(f"Tweeted: {text}")
    except Exception as e:
        print(f"Error posting tweet: {e}")

def reply_to_tweet(tweet_id, text):
    try:
        twitter.update_status(status=text, in_reply_to_status_id=tweet_id, auto_populate_reply_metadata=True)
        print(f"Replied: {text}")
    except Exception as e:
        print(f"Error replying: {e}")

def main():
    # نشر التغريدات اليومية
    if not in_sleep_hours():
        articles = get_rss_articles()
        daily_tweets = random.sample(articles, min(DAILY_TWEET_LIMIT, len(articles)))
        for tweet in daily_tweets:
            content = generate_tweet(tweet)
            post_tweet(content)
            time.sleep(10)

        # الردود على التغريدات الجديدة من الحسابات المراقبة
        for account_id in monitored_accounts:
            try:
                tweets = twitter.user_timeline(user_id=account_id, count=20)
                replied = 0
                for t in tweets:
                    if replied >= DAILY_REPLY_LIMIT:
                        break
                    if not t.favorited:
                        reply_text = generate_reply(t.text)
                        reply_to_tweet(t.id, reply_text)
                        replied += 1
                        time.sleep(5)
            except Exception as e:
                print(f"Error fetching/replying to {account_id}: {e}")

if __name__ == "__main__":
    main()
