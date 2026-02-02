import feedparser
import json
import os
import yaml

# قائمة المصادر الموثوقة 100% (يمكنك زيادتها)
SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://9to5mac.com/feed/",
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/category/security/rss",
    "https://www.reutersagency.com/feed/?best-topics=technology"
]

def load_config():
    """تحميل إعدادات مفاتيح X من الملف"""
    with open('utils/config.yaml', 'r') as f:
        return yaml.safe_load(f)

def get_verified_news():
    """جلب الأخبار وضمان الموثوقية عبر المقارنة بين المصادر (Cross-Referencing)"""
    titles_count = {}
    entries_map = {}
    
    for url in SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # تنظيف العنوان للمقارنة (إزالة المسافات الزائدة وتحويله للصغير)
                clean_title = entry.title.strip().lower()
                
                titles_count[clean_title] = titles_count.get(clean_title, 0) + 1
                if clean_title not in entries_map:
                    entries_map[clean_title] = entry
        except Exception as e:
            print(f"⚠️ خطأ في جلب المصدر {url}: {e}")
            continue

    # نختار الأخبار التي تكررت في أكثر من مصدر (تأكيد الحقيقة) 
    # أو الأخبار "العاجلة" جداً حتى لو من مصدر واحد (سيتم فحصها لاحقاً بالذكاء الاصطناعي)
    verified = []
    for title, count in titles_count.items():
        if count > 1 or "breaking" in title or "عاجل" in title:
            verified.append(entries_map[title])
            
    return verified

def load_state():
    """تحميل ذاكرة البوت لضمان عدم التكرار"""
    state_path = 'utils/state.json'
    # التأكد من وجود المجلد والملف
    if not os.path.exists('utils'):
        os.makedirs('utils')
        
    if not os.path.exists(state_path):
        initial_state = {"posted_hashes": [], "replied_ids": [], "blacklist": []}
        save_state(initial_state)
        return initial_state
        
    with open(state_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_state(state):
    """حفظ الذاكرة بعد كل عملية نشر أو رد"""
    with open('utils/state.json', 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=4)
