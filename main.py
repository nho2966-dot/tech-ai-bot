import os
import asyncio
import httpx
import tweepy
import sqlite3
import re
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "TAVILY": os.getenv("TAVILY_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"), "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"), "access_s": os.getenv("X_ACCESS_SECRET")
    }
}

client = tweepy.Client(
    consumer_key=CONF["X"]["key"], consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"], access_token_secret=CONF["X"]["access_s"]
)

# ================= 🛡️ THE ELITE FILTER (V32) =================
def elite_clean(text):
    # مسح الصيني والركاكة وتصفية النص
    text = re.sub(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]', '', text)
    forbidden = ["أهلاً بك", "في هذا المقال", "نود أن نوضح", "عصرنا الحالي"]
    for word in forbidden:
        text = text.replace(word, "")
    return text.strip()

# ================= 🔍 DEEP NEWS SEARCH =================
async def get_deep_news():
    try:
        async with httpx.AsyncClient() as c:
            # البحث عن أخبار تقنية عميقة ومحددة
            query = "cutting-edge AI tools benchmarks release 2026 agents"
            res = await c.post("https://api.tavily.com/search", json={
                "api_key": CONF["TAVILY"],
                "query": query,
                "search_depth": "advanced",
                "days": 1
            })
            return "\n".join([f"- {r['title']}: {r['content'][:300]}" for r in res.json().get('results', [])[:3]])
    except: return "Focus on Local LLMs and Autonomous Agents workflows."

# ================= 🧠 ELITE AI ENGINE =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=90) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.4,
                    "messages": [
                        {"role": "system", "content": system + """
- اللهجة: خليجية بيضاء احترافية (Professional Tech Arabic).
- الإلزام: اذكر المصطلحات التقنية الإنجليزية بين قوسين بجانب العربي (مثال: الأتمتة الذاتية (Autonomous Agents)).
- التركيز: ركز على (Workflows), (APIs), (Infrastructure), و (Latency).
- ممنوع الإنشائيات. ادخل في التفاصيل العميقة فوراً."""},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return elite_clean(res.json()["choices"][0]["message"]["content"])
    except: return None

# ================= 🚀 EXECUTION =================
async def main():
    logger.info("📡 جاري توليد محتوى تقني دسم (V32)...")
    
    news_data = await get_deep_news()
    
    sys_msg = "أنت كبير مهندسي الحلول (Senior Solution Architect). حلل الأخبار للأفراد بأسلوب تقني بحت."
    
    prompt = f"السياق التقني الحالي:\n{news_data}\n\nصمم تغريدة 'دسمة' تشرح ميزة أو أداة جديدة مع توضيح الـ (Architecture) البسيط لاستخدامها."
    
    content = await ask_ai(sys_msg, prompt)
    
    if content:
        # إضافة الوسوم الاستراتيجية
        final_post = f"🚨 التقنية بعمق (Deep Dive):\n\n{content}\n\n#AI_Architecture #DevTools #ذكاء_اصطناعي #TechDeepDive"
        
        # نشر التغريدة
        client.create_tweet(text=final_post)
        logger.success("🔥 تم نشر المحتوى الدسم بنجاح!")

if __name__ == "__main__":
    asyncio.run(main())
