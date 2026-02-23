import os
import asyncio
import random
import tweepy
import httpx
from loguru import logger
from google import genai
from openai import OpenAI
from anthropic import Anthropic  # العقل الرابع
from bs4 import BeautifulSoup

# ==========================================
# ⚙️ الربط والسيادة
# ==========================================
KEYS = {
    "GEMINI": os.getenv("GEMINI_KEY"),
    "OPENAI": os.getenv("OPENAI_API_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY"),
    "CLAUDE": os.getenv("ANTHROPIC_API_KEY") # مفتاح كلود
}

X_CRED = {
    "ck": os.getenv("X_API_KEY"), "cs": os.getenv("X_API_SECRET"),
    "at": os.getenv("X_ACCESS_TOKEN"), "ts": os.getenv("X_ACCESS_SECRET")
}

# ==========================================
# 🧠 منظومة العقول الرباعية (Succession V2)
# ==========================================
async def get_ai_response(prompt):
    brains = [
        ("Gemini", lambda p: genai.Client(api_key=KEYS["GEMINI"]).models.generate_content(model="gemini-2.0-flash", contents=p).text),
        ("Claude", lambda p: Anthropic(api_key=KEYS["CLAUDE"]).messages.create(model="claude-3-5-sonnet-20241022", max_tokens=500, messages=[{"role": "user", "content": p}]).content[0].text),
        ("OpenAI", lambda p: OpenAI(api_key=KEYS["OPENAI"]).chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":p}]).choices[0].message.content),
        ("Groq", lambda p: OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"]).chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":p}]).choices[0].message.content)
    ]
    
    for name, func in brains:
        try:
            if not KEYS.get(name.upper()) and name != "Groq": continue # Groq هو الفزعة الدائمة
            content = await asyncio.to_thread(func, prompt)
            if content: 
                logger.info(f"💡 تمت الصياغة بواسطة عقل: {name}")
                return content.strip()
        except Exception as e:
            logger.warning(f"⚠️ العقل {name} متوقف: {e}")
    return None

# ==========================================
# 🏆 نظام المسابقات والجوائز (Contests)
# ==========================================
def get_contest_prompt():
    contests = [
        "صمم سؤال مسابقة تقنية ذكي (لغز) عن أداة AI جديدة للأفراد، واطلب من المتابعين الإجابة بجوائز معنوية (دعم فني/نشر حساب).",
        "اطرح 'تحدي' للمتابعين: ابتكار فكرة لاستخدام ChatGPT في تسهيل الحياة اليومية بالخليج، وأفضل فكرة لها منشن."
    ]
    return random.choice(contests)

# ==========================================
# 🚀 التنفيذ الاستراتيجي
# ==========================================
async def run_apex_mission():
    logger.info("🔥 تشغيل نظام أيبكس الشامل...")
    client_v2 = tweepy.Client(
        consumer_key=X_CRED["ck"], consumer_secret=X_CRED["cs"],
        access_token=X_CRED["at"], access_token_secret=X_CRED["ts"]
    )

    # قرار عشوائي: خبر أو مسابقة؟
    mode = random.choice(["news", "contest"])
    
    if mode == "news":
        # كود جلب الأخبار (نفسه السابق)
        logger.info("🗞 النمط الحالي: نشر خبر سبق صحفي.")
        url = "https://news.google.com/rss/search?q=AI+tools+individuals+2026&hl=ar&gl=SA&ceid=SA:ar"
        async with httpx.AsyncClient() as c:
            r = await c.get(url)
            item = BeautifulSoup(r.text, 'xml').find('item')
            headline = item.title.text if item else "تحديثات الذكاء الاصطناعي اليوم"
            link = item.link.text if item else ""
            prompt = f"حلل الخبر بأسلوب خليجي دسم للأفراد: ({headline}). التقسيم: 🔹الخبر، ✨الخفايا، 🛠التطبيق، 📍الزبدة. (مصطلحات إنجليزية)."
    else:
        logger.info("🏆 النمط الحالي: طرح مسابقة تفاعلية.")
        prompt = get_contest_prompt() + " (اجعل الأسلوب خليجي حماسي جداً، استخدم إيموجيات)."
        link = ""

    final_text = await get_ai_response(prompt)
    
    if final_text:
        try:
            full_post = f"{final_text}\n\n🔗 {link}" if link else final_text
            client_v2.create_tweet(text=full_post)
            logger.success(f"✅ تم تنفيذ مهمة الـ {mode} بنجاح!")
        except Exception as e:
            logger.error(f"❌ خطأ تنفيذ التغريدة: {e}")

if __name__ == "__main__":
    asyncio.run(run_apex_mission())
