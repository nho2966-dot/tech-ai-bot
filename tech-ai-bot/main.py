import os
import json
import time
import logging
import argparse
import yaml
import tweepy
from datetime import datetime, timezone
from typing import List, Optional, Dict
from openai import OpenAI

# ───────────────────────────────────────────────
# 1. إعدادات المسارات والـ Config (نفس هيكلك)
# ───────────────────────────────────────────────
CONFIG_PATH = ".github/workflows/config.yaml"

try:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        CONFIG = yaml.safe_load(f)
    print("→ تم تحميل config.yaml بنجاح")
except:
    CONFIG = {}

STATE_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), CONFIG.get("paths", {}).get("state_file", "../../state.json")))

# ───────────────────────────────────────────────
# 2. الكلاس الرئيسي مع المعالجة (Hybrid Auth + Arabic Focus)
# ───────────────────────────────────────────────
class TechExpertMasterFinal:
    def __init__(self):
        # إعداد AI مع تعليمات لغوية صارمة لمنع الصينية والجفاف
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        # المصادقة الهجينة (V1 للردود و V2 للنشر) لحل خطأ 401
        self.auth = tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
        )
        self.api_v1 = tweepy.API(self.auth)
        
        self.client_v2 = tweepy.Client(
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        self.state = self._load_state()
        # التعليمات النظامية المعالجة (تجنب الجفاف واللغات الأخرى)
        self.system_instr = (
            "أنت خبير تقني عربي محترف. اكتب بلغة عربية فصحى بسيطة، مشوقة وغير جافة.\n"
            "ممنوع تماماً استخدام أي لغة غير العربية (لا صينية ولا إنجليزية).\n"
            "تأكد من أن النص كامل ومفيد وينتهي بنقطة أو سؤال تفاعلي.\n"
            "التزم بضم الشفتين عند المد بالواو (تطوير، تكنولوجيا)."
        )

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {"replied_to": [], "rotation_idx": 0}

    def _save_state(self):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def generate_content(self, prompt: str, model: str = "qwen/qwen-2.5-72b-instruct"):
        """توليد محتوى مع معالجة الجفاف واللغة"""
        try:
            res = self.ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.system_instr},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=280
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"AI Error: {e}")
            return None

    def handle_smart_replies(self):
        """المعالجة: الرد عبر v1.1 لتجاوز 401"""
        try:
            query = "برمجة OR تقنية lang:ar -is:retweet"
            tweets = self.client_v2.search_recent_tweets(query=query, max_results=5)
            
            if tweets.data:
                for tweet in tweets.data:
                    if tweet.id in self.state.get("replied_to", []): continue
                    
                    prompt = f"رد بأسلوب ذكي وودود على: {tweet.text}"
                    reply = self.generate_content(prompt, model="openai/gpt-4o-mini")
                    
                    if reply:
                        # الرد عبر V1.1 (الحل الوحيد المستقر للردود حالياً)
                        self.api_v1.update_status(
                            status=reply[:280],
                            in_reply_to_status_id=tweet.id,
                            auto_populate_reply_metadata=True
                        )
                        self.state.setdefault("replied_to", []).append(tweet.id)
                        logging.info(f"✅ تم الرد بنجاح على {tweet.id}")
                        break
        except Exception as e:
            logging.error(f"❌ خطأ في الردود: {e}")

    def handle_rotation_post(self):
        """النشر التدويري مع الحفاظ على الترتيب"""
        try:
            pillars = ["breaking_news", "ai_daily_life", "ai_tool"]
            idx = self.state.get("rotation_idx", 0)
            kind = pillars[idx % len(pillars)]
            
            prompt = f"اكتب تغريدة احترافية ومشوقة عن موضوع: {kind}"
            content = self.generate_content(prompt)
            
            if content:
                self.client_v2.create_tweet(text=content[:280])
                self.state["rotation_idx"] = idx + 1
                logging.info(f"✅ تم نشر تغريدة: {kind}")
        except Exception as e:
            logging.error(f"❌ خطأ في النشر: {e}")

    def run(self):
        self.handle_smart_replies()
        time.sleep(20) # فجوة أمان
        self.handle_rotation_post()
        self._save_state()

# ───────────────────────────────────────────────
# 3. نقطة التشغيل (نفس هيكلك)
# ───────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = TechExpertMasterFinal()
    bot.run()
