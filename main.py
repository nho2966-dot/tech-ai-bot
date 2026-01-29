import os, json, logging, tweepy, time
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

# ====== الإعدادات ======
OPENAI_MODEL = "gpt-4o-mini"
STATE_FILE = "state.json"

PERSONA_PROMPT = """
أنت صحفي تقني عربي محترف.
تشرح التقنية بلغة إنسانية، ودودة، ذكية.
لا تبالغ، لا تجزم بدون مصدر.
ابدأ دائمًا بـ Hook قوي.
أنهِ المنشور بسؤال تفاعلي.
"""

TREND_TOPICS = [
    "الذكاء الاصطناعي",
    "ChatGPT",
    "Meta",
    "Google",
    "OpenAI",
    "تحديث",
    "ميزة جديدة"
]

# ====== تشغيل البوت ======
def run_bot():
    logging.info("🚀 تشغيل الوكيل الإعلامي الاحترافي")

    client = tweepy.Client(
        bearer_token=os.environ["X_BEARER_TOKEN"],
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_SECRET"],
        wait_on_rate_limit=True
    )

    ai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    query = "(AI OR تقنية OR ذكاء_اصطناعي) lang:ar -is:retweet"
    tweets = client.search_recent_tweets(query=query, max_results=5)

    state = load_state()

    for tweet in tweets.data or []:
        if tweet.id in state["replied"]:
            continue

        content = generate_content(ai, tweet.text)
        score = evaluate_content(ai, content)

        if score < 80:
            logging.info(f"⛔ تم رفض المحتوى (Score={score})")
            continue

        client.create_tweet(
            text=content,
            in_reply_to_tweet_id=tweet.id
        )

        state["replied"].append(tweet.id)
        save_state(state)
        logging.info(f"✅ نُشر بنجاح (Score={score})")
        break

# ====== توليد المحتوى ======
def generate_content(ai, source_text):
    prompt = f"""
{PERSONA_PROMPT}

المصدر:
{source_text}

اكتب تغريدة أو ثريد قصير احترافي.
"""
    res = ai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content.strip()

# ====== تقييم المحتوى ======
def evaluate_content(ai, content):
    prompt = f"""
قيّم المحتوى التالي من 100 حسب:
- قوة البداية
- الدقة
- الأنسنة
- التفاعل

المحتوى:
{content}

أعطني رقمًا فقط.
"""
    res = ai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return int(res.choices[0].message.content.strip())
    except:
        return 0

# ====== الحالة ======
def load_state():
    if not os.path.exists(STATE_FILE):
        return {"replied": []}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

if __name__ == "__main__":
    run_bot()
