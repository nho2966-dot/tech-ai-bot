import feedparser

class TrendHunter:
    def __init__(self):
        self.sources = [
            "https://www.theverge.com/rss/index.xml",
            "https://techcrunch.com/feed/"
        ]

    def fetch_latest_news(self):
        news_list = []
        for url in self.sources:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: # جلب آخر 5 أخبار
                media_url = None
                is_video = False
                
                # استخراج الصورة من ملاحق الخبر (Enclosures) أو الـ Media Content
                if 'media_content' in entry:
                    media_url = entry.media_content[0]['url']
                elif 'links' in entry:
                    for link in entry.links:
                        if 'image' in link.get('type', ''):
                            media_url = link.get('href')
                
                news_list.append({
                    "title": entry.title,
                    "summary": entry.summary,
                    "link": entry.link,
                    "media_url": media_url,
                    "is_video": is_video # يمكن تطويرها لاحقاً لفحص الامتداد .mp4
                })
        return news_list
