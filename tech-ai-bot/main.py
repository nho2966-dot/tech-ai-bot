import os
import yaml
import logging
import tweepy
from openai import OpenAI
from datetime import datetime, timedelta
import random
import time
import hashlib

# ─── إعداد السجل (Logs) ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-5s | %(message)s',
    handlers=[logging.StreamHandler()]
)

LAST_TWEET_FILE = "last_tweet_hash.txt"

class TechAgentPro:
    def __init__(self):
        logging.info("=== TechAgent Pro v6.1 – رادار التسريبات والسبق الصحفي ===")
        
        self.config = self._load_config()

        # ─── إعداد الذكاء الاصطناعي (أولوية OpenRouter) ──────────────────────
        router_key = os.getenv("OPENROUTER_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if router_key:
            logging.info("تفعيل محرك OpenRouter (Qwen)")
            self.ai_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=router_key)
            # تم تصحيح Model ID ليعمل 100% مع OpenRouter
            self.model = "qwen/qwen-2.5-72b-instruct"
        elif openai_key:
            logging.info("تفعيل محرك OpenAI (Fallback)")
            self.ai_client = OpenAI(api_key=openai_key)
            self.model = "gpt-4o-mini"
        else:
            raise ValueError("❌ خطأ: لم يتم العثور على مفاتيح API (Secrets)")

        # ─── إعداد منصة X (Twitter) ──────────────────────────────────────────
        self.x_client = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET"),
            wait_on_rate_limit=True
        )

        try:
            me = self.x_client.get_me().data
            self.my_username = me.username
            logging.info(f"✅ متصل بحساب: @{self.my_username}")
        except Exception as e:
            logging.error(f"❌ فشل الاتصال بتويتر: {e}")
            raise

    def _load_config(self):
        secret = os.getenv("CONFIG_YAML")
        if secret:
            try:
                return yaml.safe_load(secret)
            except:
                pass
        return {
            "behavior": {
                "daily_posts_target": 2,
                "spam_keywords": ["crypto", "airdrop", "giveaway", "ربح", "مجانا"]
            }
        }

    def _was_similar_tweet_posted_today(self, content: str) -> bool:
        """منع التكرار خلال 24 ساعة عبر بصمة النص MD5"""
        if not os.path.exists(LAST_T
