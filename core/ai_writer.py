import google.generativeai as genai
import os

class AIWriter:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY غير موجود")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_practical_content(self, news_item, content_type='tweet'):
        prompts = {
            'tweet': f"اشرح هذا الخبر ببساطة مع نصيحة عملية: {news_item['summary']}",
            'tool': f"اشرح هذه الأداة التقنية وكيف توفر وقت المستخدم: {news_item['summary']}",
            'security': f"حلل الخبر أمنياً وأعطِ نصيحة حماية سهلة: {news_item['summary']}",
            'thread': f"حول هذا الخبر لثريد تعليمي بسيط: {news_item['summary']}"
        }

        prompt = prompts.get(content_type, prompts['tweet'])
        
        system_instruction = "أنت خبير تقني بأسلوب بشري بسيط جداً. لغتك العربية سليمة وغير متكلفة. ركز على الفائدة العملية فقط."
        
        response = self.model.generate_content(f"{system_instruction}\n\n{prompt}")
        return response.text.strip()

    def generate_smart_reply(self, mention_text, username):
        prompt = f"رد على المتابع {username} بأسلوب تقني ودود وقصير جداً على هذه التغريدة: {mention_text}"
        response = self.model.generate_content(prompt)
        return response.text.strip()
