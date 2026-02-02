import os
# استخدام الاستيراد المباشر للمكتبة الجديدة
try:
    from google import genai
except ImportError:
    # في حال استمر الخطأ، سنستخدم المكتبة القديمة كخيار أمان أخير
    import google.generativeai as genai_legacy

class AIWriter:
    def __init__(self):
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.groq_key = os.environ.get("GROQ_API_KEY")
        
        if self.gemini_key:
            try:
                # المحاولة مع المكتبة الجديدة
                self.gemini_client = genai.Client(api_key=self.gemini_key)
                self.use_legacy = False
            except:
                # العودة للمكتبة المستقرة إذا فشلت الجديدة
                genai_legacy.configure(api_key=self.gemini_key)
                self.use_legacy = True
        
        if self.groq_key:
            from groq import Groq
            self.groq_client = Groq(api_key=self.groq_key)

    def verify_and_generate(self, news_item):
        prompt = f"حلل وصغ كسبق صحفي أو تفنيد: {news_item['title']}"
        
        if self.gemini_key:
            try:
                if not self.use_legacy:
                    response = self.gemini_client.models.generate_content(
                        model="gemini-2.0-flash", contents=prompt)
                    return response.text
                else:
                    model = genai_legacy.GenerativeModel("gemini-1.5-flash")
                    response = model.generate_content(prompt)
                    return response.text
            except Exception as e:
                print(f"⚠️ خطأ في Gemini: {e}")
        
        # ... باقي كود Groq كما هو ...
