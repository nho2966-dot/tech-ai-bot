import feedparser, json, os

SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://9to5mac.com/feed/",
    "https://techcrunch.com/feed/",
    "https://www.wired.com/feed/category/security/rss"
]

def get_verified_news():
    titles = {}
    verified = []
    for url in SOURCES:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            t = entry.title.lower()
            titles[t] = titles.get(t, 0) + 1
            if titles[t] == 1: verified.append(entry)
    # نختار الأخبار التي ظهرت في أكثر من مصدر لضمان الموثوقية 100%
    return [e for e in verified if titles[e.title.lower()] > 1]

def load_state():
    if not os.path.exists('utils/state.json'):
        return {"posted_hashes": [], "replied_ids": [], "blacklist": []}
    with open('utils/state.json', 'r') as f: return json.load(f)

def save_state(state):
    with open('utils/state.json', 'w') as f: json.dump(state, f)
