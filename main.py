import os
import json
import hashlib
import datetime
import random
import yaml
from core.ai_writer import AIWriter
from core.publisher import Publisher
from core.trend_hunter import TrendHunter

# --- 1. إعدادات النظام والذاكرة ---
STATE_FILE = 'utils/state.json'
CONFIG_FILE = 'utils/config.yaml'

def load_config():
    """تحميل الإعدادات واستبدال متغيرات النظام (Secrets) بالقيم الحقيقية"""
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError("❌ ملف config.yaml غير موجود في مجلد utils")
        
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        # استبدال متغيرات البيئة مثل ${X_API_KEY} بقيمها من GitHub Secrets
        for key, value in os.environ.items():
            content = content.replace(f"${{{key}}}", value)
        return yaml.safe_load(content)

def load_state():
    """تحميل ذاكرة الوكيل لمنع التكرار"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"posted_hashes": [], "replied_ids": [], "last_run": ""}
    return {"posted_hashes": [], "replied_ids": [], "last_run": ""}

def save_state(state):
    """حفظ التحديثات في الذاكرة"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_scheduled_type():
    """تحديد نوع المحتوى بناءً على اليوم (خطة المحتوى الأسبوعية)"""
    day = datetime.datetime.now().strftime('%A')
    schedule = {
        'Sunday': 'thread',      # رادار الأسبوع
        'Monday': 'tool',        # مختبر الأدوات (اليوم)
        'Tuesday': 'poll',       # استطلاع رأي
        'Wednesday': 'security', # الرادار الأمني
        'Thursday': 'thread',    # كيف تعمل التقنية؟
        'Friday': 'myth',        # كشف الخرافات
        'Saturday': 'tips'       # تلميحات سريعة
    }
    return schedule.get(day, 'tweet')

# --- 2. المنطق الرئيسي للوكيل ---
def main():
    print(f"🚀 بدء تشغيل الوكيل التقني - {datetime.datetime.now()}")
    
    try:
        # تحميل الإعدادات والذاكرة
        config = load_config()
        state = load_state()
        
        # تهيئة الأدوات
        bot = AIWriter()
        pub = Publisher(config['x_api_keys'])
        hunter = TrendHunter()

        # 1. جلب الأخبار وفلترتها (شرط الارتباط 100% بالخبر)
        news_items = hunter.fetch_verified_news()
        if not news_items:
            print("⚠️ لا توجد أخبار جديدة تلبي معايير الجودة.")
            return

        # 2. تحديد نوع المنشور حسب الخطة
        post_type = get_scheduled_type()
        
        for item in news_items:
            # منع تكرار المحتوى عبر الـ Hash
            content_id = hashlib.md5(item['title'].encode()).hexdigest()
            if content_id in state['posted_hashes']:
                continue

            print(f"📝 صياغة محتوى من نوع: {post_type}")
            
            # توليد المحتوى بأسلوب بشري بسيط وقيمة عملية
            content = bot.generate_practical_content(item, content_type=post_type)
            
            # إضافة الروابط التعليمية لتعزيز المتانة
            if 'link' in item:
                content += f"\n\nللتوسع والتوثيق الرسمي 👇\n{item['link']}"

            # 3. النشر (دعم الوسائط بفضل اشتراك X)
            success = pub.post_content(
                text=content, 
                media_url=item.get('media'),
                is_poll=(post_type == 'poll')
            )
            
            if success:
                state['posted_hashes'].append(content_id)
                state['posted_hashes'] = state['posted_hashes'][-500:] # حفظ آخر 500 فقط
                print("✅ تم النشر بنجاح.")
                break # نشر واحد دسم في كل دورة

        # 4. معالجة الردود الذكية باحترافية وبساطة
        print("🔍 فحص المنشنز للرد عليها...")
        mentions = pub.get_recent_mentions()
        for mention in mentions:
            if str(mention.id) not in state.get('replied_ids', []):
                reply = bot.generate_smart_reply(mention.text, mention.user.screen_name)
                if pub.reply_to_tweet(reply, mention.id):
                    state.setdefault('replied_ids', []).append(str(mention.id))
                    print(f"💬 تم الرد على {mention.user.screen_name}")

        # حفظ الحالة النهائية
        save_state(state)
        
    except Exception as e:
        print(f"❌ حدث خطأ غير متوقع: {str(e)}")

if __name__ == "__main__":
    main()
