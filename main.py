from core.ai_writer import AIWriter
from core.publisher import Publisher
from core.trend_hunter import TrendHunter
import json, hashlib

def main():
    # 1. الإعداد
    with open('utils/config.yaml') as f: config = yaml.safe_load(f)
    bot = AIWriter()
    pub = Publisher(config['x_api_keys'])
    hunter = TrendHunter()
    
    # تحميل الذاكرة
    with open('utils/state.json', 'r+') as f: state = json.load(f)

    # 2. جلب الأخبار وفلترتها
    news = hunter.fetch_verified_news()
    for item in news:
        tag = hashlib.md5(item['title'].encode()).hexdigest()
        if tag in state['posted_hashes']: continue # منع التكرار

        # 3. اختيار نوع المحتوى عشوائياً للتنويع
        post_type = random.choice(['tweet', 'thread', 'poll', 'security'])
        content = bot.generate(item['summary'], type=post_type)

        # 4. النشر (استغلال اشتراك X)
        pub.post_content(text=content, media_url=item['media'])
        
        # 5. تحديث الذاكرة
        state['posted_hashes'].append(tag)
        break # نشر واحد في كل دورة للحفاظ على الجودة

    with open('utils/state.json', 'w') as f: json.dump(state, f)

if __name__ == "__main__":
    main()
