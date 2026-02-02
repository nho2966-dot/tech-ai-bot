import os
import json
import hashlib
import datetime
import random
import yaml
from core.ai_writer import AIWriter
from core.publisher import Publisher
from core.trend_hunter import TrendHunter

# 1. إعدادات الذاكرة ومنع التكرار
STATE_FILE = 'utils/state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"posted_hashes": [], "replied_users": {}, "last_run": ""}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_content_type_by_day():
    """تحديد نوع المحتوى بناءً على خطة الأسبوع الذكية"""
    day = datetime.datetime.now().strftime('%A')
    schedule = {
        'Sunday': 'thread',      # رادار الأسبوع (تلخيص)
        'Monday': 'tool',        # مختبر الأدوات (قيمة عملية)
        'Tuesday': 'poll',       # استطلاع رأي (تفاعل)
        'Wednesday': 'security', # الرادار الأمني (حماية)
        'Thursday': 'thread',    # كيف تعمل التقنية؟ (عمق)
        'Friday': 'myth',        # كشف الخرافات (تصحيح)
        'Saturday': 'tips'       # تلميحات سريعة (لايف هاكس)
    }
    return schedule.get(day, 'tweet')

# 2. المنطق الرئيسي للوكيل
def main():
    print(f"🚀 بدء تشغيل الوكيل التقني - {datetime.datetime.now()}")
    
    # تحميل الإعدادات والذاكرة
    try:
        with open('utils/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("❌ ملف config.yaml غير موجود")
        return

    state = load_state()
    bot = AIWriter()
    pub = Publisher(config['x_api_keys'])
    hunter = TrendHunter()

    # جلب الأخبار والتحقق من جودتها
    news_items = hunter.fetch_verified_news()
    if not news_items:
        print("⚠️ لم يتم العثور على أخبار جديدة ذات قيمة.")
        return

    # اختيار نوع المحتوى حسب اليوم
    scheduled_type = get_content_type_by_day()
    
    for item in news_items:
        # إنشاء بصمة فريدة للخبر لمنع التكرار
        content_id = hashlib.md5(item['title'].encode()).hexdigest()
        
        if content_id in state['posted_hashes']:
            continue # الخبر تم نشره مسبقاً

        print(f"📝 معالجة محتوى من نوع: {scheduled_type} للخبر: {item['title']}")
        
        # توليد المحتوى (بشري، بسيط، ذو قيمة عملية)
        final_content = bot.generate_practical_content(item, content_type=scheduled_type)
        
        # إضافة رابط المصدر أو التوثيق لزيادة المتانة
        if 'link' in item:
            final_content += f"\n\nللتفاصيل والتوثيق الرسمي 👇\n{item['link']}"

        # النشر عبر X (دعم الوسائط بفضل الاشتراك)
        try:
            success = pub.post_content(
                text=final_content, 
                media_url=item.get('media'),
                is_poll=(scheduled_type == 'poll')
            )
            
            if success:
                state['posted_hashes'].append(content_id)
                state['last_run'] = str(datetime.date.today())
                print("✅ تم النشر بنجاح وتحديث الذاكرة.")
                break # نكتفي بنشر واحد عالي الجودة في كل دورة
        except Exception as e:
            print(f"❌ فشل النشر: {e}")

    # 3. معالجة الردود الذكية (Smart Replies)
    # فحص المنشنز والرد عليها بأسلوب خبير بسيط
    try:
        mentions = pub.get_recent_mentions()
        for mention in mentions:
            if str(mention.id) not in state.get('replied_ids', []):
                reply_text = bot.generate_smart_reply(mention.text, mention.user.screen_name)
                pub.reply_to_tweet(reply_text, mention.id)
                if 'replied_ids' not in state: state['replied_ids'] = []
                state['replied_ids'].append(str(mention.id))
    except Exception as e:
        print(f"⚠️ خطأ أثناء معالجة الردود: {e}")

    # حفظ حالة الوكيل النهائية
    save_state(state)

if __name__ == "__main__":
    main()
