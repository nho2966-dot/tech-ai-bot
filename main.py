import os
import asyncio
import random
import tweepy
import pytz
from datetime import datetime
from loguru import logger
from google import genai
from openai import OpenAI
from anthropic import Anthropic
from bs4 import BeautifulSoup
import httpx

# ==========================================
# ⚙️ منظومة المفاتيح والسيادة (Secrets)
# ==========================================
KEYS = {
    "GEMINI": os.getenv("GEMINI_KEY"),
    "CLAUDE": os.getenv("ANTHROPIC_API_KEY"),
    "OPENAI": os.getenv("OPENAI_API_KEY"),
    "GROQ": os.getenv("GROQ_API_KEY")
}

X_CRED = {
    "consumer_key": os.getenv("X_API_KEY"),
    "consumer_secret": os.getenv("X_API_SECRET"),
    "access_token": os.getenv("X_ACCESS_TOKEN"),
    "access_token_secret": os.getenv("X_ACCESS_SECRET")
}

# ==========================================
# 🧠 محرك العقول المتعاقبة (Succession Engine)
# ==========================================
async def get_ai_response(prompt):
    """ينتقل بين العقول لضمان عدم توقف الخدمة وصياغة لغة راقية"""
    brains = [
        ("Gemini", lambda p: genai.Client(api_key=KEYS["GEMINI"]).models.generate_content(model="gemini-2.0-flash", contents=p).text),
        ("Claude", lambda p: Anthropic(api_key=KEYS["CLAUDE"]).messages.create(model="claude-3-5-sonnet-20241022", max_tokens=800, messages=[{"role": "user", "content": p}]).content[0].text),
        ("OpenAI", lambda p: OpenAI(api_key=KEYS["OPENAI"]).chat.completions.create(model="gpt-4o", messages=[{"role":"user","content":p}]).choices[0].message.content),
        ("Groq", lambda p: OpenAI(base_url="https://api.groq.com/openai/v1", api_key=KEYS["GROQ"]).chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user","content":p}]).choices[0].message.content)
    ]
    
    for name, func in brains:
        try:
            if not KEYS.get(name.upper()) and name != "Groq": continue
            content = await asyncio.to_thread(func, prompt)
            if content:
                logger.info(f"💡 تمت الصياغة بواسطة عقل: {name}")
                return content.strip()
        except Exception as e:
            logger.warning(f"⚠️ العقل {name} في حالة استراحة: {e}")
    return None

# ==========================================
# 🗞️ رادار الأخبار (لحصاد الجمعة)
# ==========================================
async def fetch_weekly_news():
    url = "https://news.google.com/rss/search?q=AI+tools+for+individuals+this+week&hl=ar&gl=SA&ceid=SA:ar"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            items = BeautifulSoup(r.text, 'xml').find_all('item')[:5]
            return "\n".join([f"- {i.title.text}" for i in items])
    except: return "أحدث أدوات الذكاء الاصطناعي وتطبيقاتها الإنتاجية."

# ==========================================
# 🎯 المهمة التنفيذية (ساعة أيبكس 1:00 ظهراً)
# ==========================================
async def run_apex_system():
    gulf_tz = pytz.timezone('Asia/Riyadh')
    logger.info("🔥 منظومة أيبكس تعمل الآن.. ننتظر ساعة الذروة (1:00 PM).")
    
    client_v2 = tweepy.Client(**X_CRED, wait_on_rate_limit=True)

    while True:
        now = datetime.now(gulf_tz)
        
        # التوقيت المستهدف: الساعة 1 ظهراً بتوقيت مكة/مسقط
        if now.hour == 13 and now.minute == 0:
            day_name = now.strftime('%A')
            
            if day_name == 'Friday':
                # --- نمط حصاد الجمعة (رصين ومعرفي) ---
                logger.info("🌴 بدأت مهمة حصاد الجمعة التقني...")
                raw_news = await fetch_weekly_news()
                prompt = (
                    f"استناداً لهذه الأخبار: ({raw_news})\n"
                    "اكتب 'حصاد الجمعة التقني' للأفراد بأسلوب خليجي أبيض، رزين ووقور.\n"
                    "التركيز على أفضل 3 أدوات (AI Tools) ترفع الإنتاجية. استخدم إيموجيات هادئة ومصطلحات إنجليزية (بين قوسين)."
                )
                final_text = await get_ai_response(prompt)
                if final_text:
                    client_v2.create_tweet(text=f"📌 حصاد أيبكس للأسبوع:\n\n{final_text}")
                    logger.success("✅ تم نشر حصاد الجمعة!")

            else:
                # --- نمط مسابقة الأسبوع (تفاعلية Poll) ---
                logger.info(f"🎁 بدأت مهمة مسابقة يوم {day_name}...")
                prompt = (
                    "صمم سؤال مسابقة تقنية ذكي (اختيار من متعدد) للأفراد.\n"
                    "اللغة: خليجية بيضاء راقية. التنسيق: السطر الأول السؤال، السطر الثاني 4 خيارات تفصلها فاصلة.\n"
                    "تنبيه: يجب أن تكون الخيارات قصيرة جداً (كلمة أو كلمتين)."
                )
                raw_quiz = await get_ai_response(prompt)
                if raw_quiz and "\n" in raw_quiz:
                    lines = raw_quiz.split("\n")
                    question = lines[0].strip()
                    options = [o.strip() for o in lines[1].split(",")][:4]
                    try:
                        client_v2.create_tweet(text=f"🎁 مسابقة أيبكس اليومية:\n\n{question}", 
                                             poll_options=options, 
                                             poll_duration_minutes=1440)
                        logger.success("✅ تم نشر المسابقة بنجاح!")
                    except Exception as e: logger.error(f"X Poll Error: {e}")

            await asyncio.sleep(61) # منع التكرار في نفس الدقيقة
        
        await asyncio.sleep(30) # فحص الوقت كل 30 ثانية

if __name__ == "__main__":
    # تشغيل المنظومة
    try:
        asyncio.run(run_apex_system())
    except KeyboardInterrupt:
        logger.info("👋 تم إيقاف المنظومة يدوياً.")
