import os
import tweepy
import google.genai as genai
import requests
import logging
import hashlib
import random
from datetime import datetime
from dotenv import load_dotenv

# 1. إعدادات النظام
load_dotenv()
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ملف حفظ الهاش لمنع التكرار
LAST_HASH_FILE = "last_hash.txt"

# 2. وظائف الحماية والتدقيق
def get_content_hash(text: str) -> str:
    """توليد بصمة رقمية للنص."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def is_duplicate(content: str) -> bool:
    """التحقق من التكرار مع معالجة أخطاء الملفات."""
    current_hash = get_content_hash(content)
    try:
        if os.path.exists(LAST_HASH_FILE):
            with open(LAST_HASH_FILE, "r", encoding="utf-8") as f:
                if f.read().strip() == current_hash:
                    logging.info("🚫 محتوى مكرر تم رصده — إلغاء النشر.")
                    return True
        
        # حفظ الهاش الجديد
        with open(LAST_HASH_FILE, "w", encoding="utf-8") as f:
            f.write(current_hash)
        return False
    except Exception as e:
        logging.warning(f"⚠️ تنبيه في ملف الهاش: {e}")
        return False

# 3. محرك توليد المحتوى الاحترافي
def generate_tech_content():
    """توليد تغريدة تقنية معتمدة على مصادر عالمية."""
    
    trusted_sources = [
        "The Verge", "TechCrunch", "GSMArena", "Wired", 
        "Reuters Tech", "Bloomberg Technology", "9to5Mac"
    ]
    source = random.choice(trusted_sources)

    prompt = f"""
    اكتب تغريدة تقنية احترافية جداً بالعربية الفصحى بناءً على أخبار موثوقة من ({source}).
    
    الهيكل المطلوب:
    🛡️ التقنية: (
