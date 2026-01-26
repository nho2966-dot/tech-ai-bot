import os
import logging
import tweepy
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import textwrap
import random
import time

# نظام حماية واستيراد مكتبات اللغة العربية (RTL)
try:
    from bidi.algorithm import get_display
    import arabic_reshaper
    AR_SUPPORT = True
except ImportError:
    AR_SUPPORT = False
    logging.warning("⚠️ مكتبات RTL مفقودة! سيتم عرض النص بشكل مبسط.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class TechAgentUltimate:
    def __init__(self):
        logging.info("=== TechAgent Pro v73.2 [Stable & Engaging] ===")
        
        # إعداد الاتصال بـ OpenRouter و X API
        self.ai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        auth = tweepy.OAuth1UserHandler(
            os.getenv("X_API_KEY"), os.getenv("X_API_SECRET"),
            os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET")
        )
        self.api_v1 = tweepy.API(auth)
        self.client_v2 = tweepy.Client(
            bearer_token=os.getenv("X_BEARER_TOKEN"),
            consumer_key=os.getenv("X_API_KEY"),
            consumer_secret=os.getenv("X_API_SECRET"),
            access_token=os.getenv("X_ACCESS_TOKEN"),
            access_token_secret=os.getenv("X_ACCESS_SECRET")
        )

        # التعليمات البرمجية لنبرة الصوت (سلسة، تسويقية، وجدلية)
        self.system_instr = (
            "أنت TechAgent، خبير تقني وصانع محتوى مؤثر. "
            "أسلوبك: ابدأ بـ Hook خاطف يثير الفضول. "
            "استخدم المصطلحات التقنية بالإنجليزية (Technical Terms) مع شرحها العربي في السياق. "
            "يجب أن تنتهي كل تغريدة بسؤال جدلي يثير النقاش ويقسم الآراء بقوة. "
            "تحدث بلهجة بيضاء محترفة ومحفزة. الختم دائماً بـ +#."
        )

    def _fix_text(self, text):
        """تجهيز النص العربي لضمان العرض الصحيح ومنع تقطع الحروف"""
        if AR_SUPPORT:
            reshaped_text = arabic_reshaper.reshape(text)
            return get_display(reshaped_text)
