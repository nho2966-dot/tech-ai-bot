import time
import hashlib
from core.ai_writer import AIWriter
from core.publisher import Publisher
from utils.helpers import get_verified_news, load_config, load_state, save_state

def get_content_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def run_bot():
    print(f"🚀 بدء التشغيل - {time.ctime()}")
    config = load_config()
    state = load_state()
    writer = AIWriter()
    publisher = Publisher(config['x_api_keys'])
    bot_id = str(publisher.client.get_me().data.id)

    # 1. الرصد والسبق وتفنيد الإشاعات
    news = get_verified_news()
    for item in news:
        content = writer.verify_and_generate(item)
        if not content: continue
        
        c_hash = get_content_hash(content)
        if c_hash not in state.get('posted_hashes', []):
            if publisher.post_content(content):
                state['posted_hashes'].append(c_hash)
                save_state(state)
                print("✅ تم نشر سبق صحفي جديد.")
                break # نشر خبر واحد دسم في كل دورة

    # 2. الردود الذكية الاستهدافية (مع القائمة السوداء ومنع التكرار)
    mentions = publisher.get_recent_mentions()
    for tweet in mentions:
        user_id = str(tweet.author_id)
        tweet_id = str(tweet.id)

        # شروط الانضباط: ليس أنا، ليس في القائمة السوداء، لم أرد عليه سابقاً
        if user_id == bot_id: continue
        if user_id in state.get('blacklist', []): continue
        if tweet_id in state.get('replied_ids', []): continue

        reply = writer.generate_smart_reply(tweet.text, user_id)
        if publisher.reply_to_tweet(reply, tweet.id):
            state['replied_ids'].append(tweet_id)
            save_state(state)
            print(f"💬 تم الرد على {user_id}")

if __name__ == "__main__":
    run_bot()
