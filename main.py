import os, sqlite3, logging, hashlib, re, time
from datetime import datetime
import tweepy
from openai import OpenAI

class TechThreadUltimate:
    def __init__(self, client_x, ai_client):
        self.x = client_x
        self.ai = ai_client
        self.max_len = 250

    def _dedupe_terms(self, text):
        """منع تكرار المصطلحات الإنجليزية لضمان رصانة النص"""
        seen = set()
        words = text.split()
        out = []
        for w in words:
            # تنظيف الكلمة من القوسين للفحص
            clean_w = re.sub(r"[()]", "", w).lower()
            if clean_w.isascii() and len(clean_w) > 2:
                if clean_w in seen: continue
                seen.add(clean_w)
            out.append(w)
        return " ".join(out)

    def _sanitize_tweets(self, tweets):
        clean = []
        for t in tweets:
            t = self._dedupe_terms(t.strip())
            if len(t) < 45: continue
            if len(t) > self.max_len:
                t = t[:self.max_len - 3] + "..."
            clean.append(t)
        return clean

    def post_thread(self, raw_content, source_url):
        # 1. توليد الثريد الأولي عبر AI
        prompt = "حوّل النص إلى ثريد خليجي نخبوي (Hook -> Analysis -> Takeaway) مع فواصل '---'."
        raw_res = self.ai.chat.completions.create(
            model="qwen/qwen-2.5-72b-instruct",
            messages=[{"role": "user", "content": raw_content}], temperature=0.5
        ).choices[0].message.content.strip().split("---")

        tweets = self._sanitize_tweets(raw_res)
        if len(tweets) < 3: return

        # 2. Semantic Hook Guard (رفع الـ Average Read Time)
        if not re.search(r"(ليش|كيف|وش|هل|السبب|الفرق)", tweets[0]):
            tweets[0] = "ليش هذا الموضوع مهم الحين؟ خلّك معي في هالتحليل.. 👇\n\n" + tweets[0]
        
        # 3. التأكد من وجود إيموجي جاذب في الـ Hook
        if not re.search(r"[!?🔥🚨🧠]", tweets[0]):
            tweets[0] = "🧠 " + tweets[0]

        previous_tweet_id = None
        for i, tweet_text in enumerate(tweets):
            # 4. Takeaway Guard (مضاعفة التفاعل في آخر تغريدة)
            if i == len(tweets)-1:
                if "؟" not in tweet_text:
                    tweet_text += "\n\nوش رأيك في هالنقطة؟ تتفق معي أو عندك وجهة نظر ثانية؟ 👇"
                footer = f"\n\n🔗 المصدر: {source_url}"
            else:
                footer = ""

            header = "🧵 بداية التحليل\n" if i == 0 else f"↳ {i+1}/{len(tweets)}\n"
            final_text = f"{header}{tweet_text}{footer}"

            try:
                # 5. التوقيت الذكي (Smart Indexing Timing)
                time.sleep(1.2 if i == 0 else 0.7)
                
                response = self.x.create_tweet(
                    text=final_text,
                    in_reply_to_tweet_id=previous_tweet_id if i > 0 else None
                )
                previous_tweet_id = response.data["id"]
                logging.info(f"✅ تم نشر الجزء {i+1}")
            except Exception as e:
                logging.error(f"❌ خطأ: {e}")
                break

        return previous_tweet_id
