import os
import asyncio
import httpx
import tweepy
import random
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ================= 🔐 CONFIG =================
CONF = {
    "GROQ": os.getenv("GROQ_API_KEY"),
    "X": {
        "key": os.getenv("X_API_KEY"),
        "secret": os.getenv("X_API_SECRET"),
        "token": os.getenv("X_ACCESS_TOKEN"),
        "access_s": os.getenv("X_ACCESS_SECRET"),
        "bearer": os.getenv("X_BEARER_TOKEN")
    }
}

client = tweepy.Client(
    bearer_token=CONF["X"]["bearer"],
    consumer_key=CONF["X"]["key"],
    consumer_secret=CONF["X"]["secret"],
    access_token=CONF["X"]["token"],
    access_token_secret=CONF["X"]["access_s"]
)

# ================= 🧠 محرك "المخططات العملية" (PRACTICAL BLUEPRINTS) =================
async def ask_ai(system, prompt):
    try:
        async with httpx.AsyncClient(timeout=90) as client_http:
            res = await client_http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {CONF['GROQ']}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "temperature": 0.6,
                    "messages": [
                        {"role": "system", "content": system + "\n- ركز على: (الأدوات المستخدمة + طريقة الربط + الفائدة الملموسة).\n- لهجة خليجية بيضاء رصينة وعملية.\n- استخدم التنسيق الواضح جداً (1. 2. 3.)."},
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return None

async def generate_actionable_blueprint():
    """توليد أدلة تطبيقية عملية للأفراد"""
    scenarios = [
        "بناء 'مساعد بحثي' شخصي يقرأ ملفات الـ PDF الطويلة ويلخص الأجزاء الحساسة في Notion آلياً.",
        "سير عمل (Workflow) لاستخراج البيانات من فيديوهات YouTube وتحويلها لدروس تعليمية منظمة باستخدام AI.",
        "طريقة أتمتة الردود الذكية على رسائل العمل باستخدام (AI Agents) تفهم سياق مشاريعك السابقة.",
        "كيفية بناء 'لوحة تحكم' (Dashboard) ذكية تتابع تحديثات أدواتك المفضلة وتعطيك ملخص يومي مركز.",
        "نظام 'أرشفة ذكي' يحول ملاحظاتك الصوتية العشوائية إلى مهام منظمة في تطبيقات الإنجاز (Todoist/TickTick)."
    ]
    
    scenario = random.choice(scenarios)
    
    sys_msg = """أنت خبير أتمتة عمليات (Automation Workflow Architect).
    - هدفك الوحيد: أن يخرج القارئ بخطوات تطبيقية (Actionable Steps).
    - الهيكل المطلوب: 
      1. [المشكلة]: وش العائق؟
      2. [الأدوات]: وش نحمل/نستخدم؟ (مثال: n8n, Make, OpenAI API, Python).
      3. [التطبيق]: الخطوات التقنية للربط (Logic).
      4. [القيمة]: وش بنستفيد فعلياً؟
    - كن دقيقاً جداً في ذكر أسماء التقنيات."""
    
    prompt = f"صمم مخططاً تطبيقياً وعملياً لـ: {scenario}"
    return await ask_ai(sys_msg, prompt)

# ================= 🚀 EXECUTION =================
async def main():
    logger.info("🛠️ بدء توليد المحتوى التطبيقي (V19)...")
    try:
        # توليد المخطط العملي
        blueprint = await generate_actionable_blueprint()
        
        if blueprint:
            # النشر كـ "تغريدة طويلة" بفضل اشتراك بريميوم
            # سنضيف مقدمة ثابتة لتعزيز الهوية التقنية للحساب
            final_content = f"📌 مخطط عملي (Practical Blueprint):\n\n{blueprint}\n\n#أتمتة #ذكاء_اصطناعي #الجيل_الرابع"
            
            client.create_tweet(text=final_content)
            logger.success("🔥 تم نشر الدليل التطبيقي بنجاح!")
            
    except Exception as e:
        logger.error(f"❌ خطأ في التنفيذ: {e}")

if __name__ == "__main__":
    asyncio.run(main())
