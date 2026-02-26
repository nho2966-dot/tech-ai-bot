import os
import sys
import tweepy
from dotenv import load_dotenv

load_dotenv()

def strict_test():
    print("🔍 جاري فحص المفاتيح والاتصال بمنصة X...")
    
    # استخدام Client v2
    client = tweepy.Client(
        bearer_token=os.getenv("X_BEARER_TOKEN"),
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET")
    )
    
    try:
        # 1. فحص القراءة
        me = client.get_me()
        print(f"✅ نجحت القراءة. تم التعرف على الحساب: {me.data.username}")
        
        # 2. فحص الكتابة (النشر)
        print("⏳ جاري محاولة النشر...")
        response = client.create_tweet(text="تحديث: أدوات الذكاء الاصطناعي للأفراد تطور بشكل متسارع. (تغريدة فحص السيرفر) 🤖🚀")
        print(f"🎉 تم النشر بنجاح! رقم التغريدة: {response.data['id']}")
        
    except tweepy.errors.Unauthorized as e:
        print("\n❌ خطأ 401: المفاتيح غير صالحة أو تحتاج Regenerate.")
        print(f"تفاصيل تقنية: {e}")
        sys.exit(1)  # إجبار GitHub على إظهار خطأ أحمر
        
    except tweepy.errors.Forbidden as e:
        print("\n❌ خطأ 403: المفاتيح سليمة لكنها للقراءة فقط! (Read Only).")
        print(f"تفاصيل تقنية: {e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    strict_test()
