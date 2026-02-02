from datetime import datetime
import random

def is_peak_time(peak_hours):
    return datetime.now().hour in peak_hours

def choose_post_type():
    return random.choice(["tweet", "thread"])
SOURCES = [
    "https://www.theverge.com/rss/index.xml",      # المصدر الأول عالمياً
    "https://9to5mac.com/feed/",                   # أخبار أبل العاجلة
    "https://techcrunch.com/feed/",                # أخبار الشركات والشركات الناشئة
    "https://www.bloomberg.com/feeds/technology/sitemap_news.xml", # أخبار اقتصاد التقنية الموثوقة
    "https://www.reutersagency.com/feed/?best-topics=technology" # وكالة رويترز (للأخبار المؤكدة 100%)
]
