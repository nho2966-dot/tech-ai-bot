import os
import tweepy
import requests
import logging
import random
from datetime import datetime
from dotenv import load_dotenv

# ✅ إعدادات الـوُضُـوح
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [MASTER-AI] - %(message)s')

client = tweepy.Client(
    bearer_token=os.getenv("X_BEARER_TOKEN"),
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_API_SECRET"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

ARCHIVE_FILE = "published_archive.txt"

def is_duplicate(identifier):
    if not os.path.exists(ARCHIVE_FILE): return False
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        return identifier.lower()[:60] in f.read().lower()

def save_to_archive(identifier):
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}: {identifier}\n")

def generate_ai_content(prompt_type, topic_or_msg, username=""):
    try:
        # 🌟 صياغة البرومبت ليشمل كافة المجالات المتفق عليها بـوُضُـوح
        if prompt_type == "post":
            system_persona = (
                "أنت 'Cyber Hunter' - خبير تقني شامل. "
                "تخصصك: (الذكاء الاصطناعي، الجيمنج، الأمن السيبراني، تسريبات الأجهزة، نصائح تقنية يومية). "
                "الهيكل الصارم للتغريدة: "
                "1. الود: ابدأ بـ 'أهلاً بكم يا رفاق التقنية..' "
                "2. [TITLE]: عنوان مثير وحاسم. "
                "3. Hook: جملة جاذبة عن (الثغرة، الجهاز، أو النصيحة). "
                "4. التفاصيل: 3 نقاط دسمة تشرح 'كيفية الاستفادة من هذه التقنية في حياتنا اليومية'. "
                "5. الخاتمة: سؤال مباشر وصريح للمتابع (أنت) لفتح نقاش. "
                "القاعدة: يجب أن يكون النص مكتملاً وأقل من 280 حرفاً بـوُضُـوح."
            )
            user_msg = f"اكتب تقريراً مكتملاً ومفيداً حول: {topic_or_msg}"
        
        else:
            system_persona = (
                f"أنت 'Cyber Hunter'. رد بـود وحسم على @{username}. "
                "قدم نصيحة تقنية أو معلومة دسمة وانتهِ بسؤال مباشر له (أنت). "
                "الاختصار شرط أساسي (أقل من 200 حرف)."
            )
            user_msg = f"رد على المنشن: {topic_or_msg}"

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
            json={
                "model": "meta-llama/llama-3.1-70b-instruct",
                "messages": [{"role": "system", "content": system_persona}, {"role": "user", "content": user_msg}],
                "temperature": 0.6,
                "max_tokens": 350
            }, timeout=60
        )
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"❌ AI Error: {e}")
        return None

def post_scoop():
    # 🌟 قائمة المواضيع الشاملة كما تم الاتفاق عليها سابقا بـوُضُـوح
    categories = [
        "أحدث تسريبات هواتف iPhone و Samsung القادمة وكيف ستغير تجربة المستخدم",
        "ثغرة أمنية جديدة في أنظمة الأندرويد وكيف تحمي بياناتك الشخصية اليوم",
        "مستقبل الجيمنج: كيف سيغير الذكاء الاصطناعي جرافيك الألعاب وتجربة اللعب",
        "نصيحة تقنية: طرق مبتكرة لزيادة عمر بطارية لابتوبك باستخدام إعدادات مخفية",
        "أمن المعلومات: كيف تكتشف محاولات الاختراق عبر الهندسة الاجتماعية في حياتك اليومية",
        "مقارنة بين أحدث كروت الشاشة للجيمنج: هل تستحق الترقية الآن؟",
        "كيف تستخدم أدوات الذكاء الاصطناعي لتوفير 3 ساعات من عملك اليومي"
    ]
    topic = random.choice(categories)
    if is_duplicate(topic): return

    content = generate_ai_content("post", topic)
    if content:
        try:
            client.create_tweet(text=content[:280])
            save_to_archive(topic)
            logging.info(f"✅ تم نشر المحتوى الشامل (أمن/جيمنج/تسريبات) بـوُضُـوح.")
        except Exception as e:
            logging.error(f"❌ فشل النشر: {e}")

def auto_reply():
    try:
        me = client.get_me().data
        mentions = client.get_users_mentions(id=me.id, expansions=['author_id'], user_fields=['username'])
        if not mentions or not mentions.data: return
        
        users = {u['id']: u['username'] for u in mentions.includes['users']}
        for tweet in mentions.data:
            reply_id = f"reply_{tweet.id}"
            if is_duplicate(reply_id): continue
            
            author_username = users.get(tweet.author_id)
            reply_text = generate_ai_content("reply", tweet.text, author_username)
            if reply_text:
                client.create_tweet(text=f"@{author_username} {reply_text}"[:280], in_reply_to_tweet_id=tweet.id)
                save_to_archive(reply_id)
                logging.info(f"💬 رد ودي وحاسم على @{author_username}")
    except Exception as e:
        logging.error(f"❌ فشل الرد: {e}")

if __name__ == "__main__":
    post_scoop()
    auto_reply()
