import os
from google import genai
from utils.helpers import get_config # استخدام الهيلبر الموجود عندك

class AIWriter:
    def __init__(self):
        self.config = get_config()
        self.client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        self.model = "gemini-1.5-flash"

    async def generate_apex_secret(self, trend_context=""):
        # قراءة البرومبت من الملف الموجود في مجلد prompts
        with open('prompts/tweet.txt', 'r', encoding='utf-8') as f:
            base_prompt = f.read()

        full_prompt = f"""
        {base_prompt}
        الترند الحالي: {trend_context}
        المهمة: اكتب سر تقني (Artificial Intelligence and its latest tools) بلهجة خليجية بيضاء.
        التنسيق: 
        - جمل قصيرة ومشوقة.
        - تحدي تفاعلي في النهاية.
        - الهاشتاجات: #أيبكس_تقني #AI_Secrets #2026
        """
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt
        )
        return response.text.strip()
