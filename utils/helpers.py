from datetime import datetime
import random

def get_dynamic_priority(news_item):
    """تحديد أولوية الخبر بناءً على الكلمات المفتاحية للسبق الصحفي"""
    urgent_keywords = ['breaking', 'urgent', 'apple', 'nvidia', 'openai', 'leaks', 'عاجل', 'تسريبات']
    title = news_item['title'].lower()
    
    # إذا كان الخبر يحتوي على كلمة عاجلة، نعطيه أولوية القصوى
    if any(word in title for word in urgent_keywords):
        return "urgent_tweet" # تغريدة عاجلة فورية
    return "normal"

def choose_post_type(priority):
    """اختيار التنسيق بناءً على الأولوية"""
    if priority == "urgent_tweet":
        return "tweet" # السبق الصحفي يفضل أن يكون تغريدة سريعة
    return random.choice(["tweet", "thread", "tool", "poll"])

def is_peak_time():
    """تحديد أوقات الذروة في منطقتنا (مثلاً من 4 عصراً إلى 10 مساءً)"""
    current_hour = datetime.now().hour
    peak_hours = range(16, 23) 
    return current_hour in peak_hours
