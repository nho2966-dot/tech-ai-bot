import random

TREND_TOPICS = [
    "OpenAI تطلق ميزة جديدة قد تغيّر طريقة استخدام الذكاء الاصطناعي",
    "أداة ذكاء اصطناعي تختصر ساعات العمل إلى دقائق",
    "تحديث جديد في منصة X يهم صناع المحتوى",
    "شركة ناشئة تستخدم AI بطريقة صادمة",
    "كيف سيغيّر الذكاء الاصطناعي مستقبل الوظائف قريبًا؟",
    "ميزة مخفية في ChatGPT لا يعرفها الكثير",
    "منصات التواصل تدخل عصر الذكاء الاصطناعي"
]

def get_trending_topic(used_topics):
    topic = random.choice(TREND_TOPICS)
    while topic in used_topics:
        topic = random.choice(TREND_TOPICS)
    return topic
