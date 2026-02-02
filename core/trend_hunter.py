import feedparser

class TrendHunter:
    def fetch_verified_news(self):
        # مصادر عالمية موثوقة
        sources = ["https://techcrunch.com/feed/", "https://www.theverge.com/rss/index.xml"]
        verified_items = []
        for src in sources:
            feed = feedparser.parse(src)
            for entry in feed.entries[:3]:
                # فلتر عدم السطحية
                if len(entry.summary) > 100: 
                    verified_items.append({
                        'title': entry.title,
                        'summary': entry.summary,
                        'link': entry.link,
                        'media': entry.enclosures[0].href if entry.enclosures else None
                    })
        return verified_items
