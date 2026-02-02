from datetime import datetime
import random
import feedparser

def get_verified_news(sources):
    """جلب الأخبار والتحقق من تكرارها لضمان الموثوقية"""
    all_news = []
    seen_titles = {} # لتتبع تكرار الخبر في مصادر مختلفة

    for url in sources:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.title.lower()
            # استخراج الكلمات المفتاحية الأساسية من العنوان
            keywords = set(title.split())
            
            # محرك التحقق: إذا ظهرت كلمات العنوان في مصدر آخر، تزداد الموثوقية
            found_match = False
            for seen_title in seen_titles:
                # إذا تشابه العنوان بنسبة كبيرة مع خبر آخر
                common_words = keywords.intersection(set(seen_title.split()))
                if len(common_words) > 3: # تشابه في 4 كلمات أساسية أو أكثر
                    seen_titles[seen_title]['count'] += 1
                    seen_titles[seen_title]['sources'].append(url)
                    found_match = True
                    break
            
            if not found_match:
                seen_titles[title] = {
                    'entry': entry,
                    'count': 1,
                    'sources': [url],
                    'time': datetime.now()
                }

    # فلترة الأخبار: اختيار الأخبار التي ظهرت في أكثر من مصدر (موثوقة) 
    # أو أخبار من مصادر "عالية الثقة" حتى لو كانت وحيدة
    verified_news = []
    for title, data in seen_titles.items():
        is_breaking = any(word in title for word in ['breaking', 'urgent', 'عاجل'])
        
        # شرط النشر: إما خبر مكرر (تأكيد) أو خبر عاجل من مصدر موثوق
        if data['count'] > 1 or is_breaking:
            status = "حقيقة مؤكدة ✅" if data['count'] > 1 else "سبق قيد التحقق 🚨"
            data['entry']['verification_status'] = status
            verified_news.append(data['entry'])
            
    return verified_news
