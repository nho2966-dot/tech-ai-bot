from google import genai
import os
import re

try:
    from groq import Groq
except ImportError:
    pass

class AIWriter:
    def __init__(self):
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.groq_key = os.environ.get("GROQ_API_KEY")
        
        # تهيئة عميل Gemini (الخيار الأول)
        if self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)
        
        # تهيئة عميل Groq (الخيار الاحتياطي)
        if self.groq_key:
            self.groq_client = Groq(api_key=self.groq_key)

    def clean_output(self, text):
        """تنظيف النص المنتج من الرموز الزائدة والتأكد من الطول"""
        # إزالة علامات الاقتباس الزائدة التي تضعها النماذج أحياناً
        text = text.replace('"', '').replace('**', '')
        # التأكد من عدم تجاوز طول التغريدة (تقريباً 280 حرف للعامة، وأكثر للمشتركين)
        # بما أنك مشترك X، سأترك السقف مرتفعاً ولكن بحدود معقولة
        return text[:2000].strip()

    def verify_and_generate(self, news_item):
        """رصد السبق وتفنيد الإشاعات بذكاء اصطناعي مزدوج"""
        
        fact_check_prompt = f"""
        بصفتك خبيراً تقنياً ومحققاً في الأخبار:
        الخبر: {news_item.get('title', '')}
        المحتوى: {news_item.get('summary', '')}
        
        المهمة:
        1. إذا كان المصدر رسمياً (مثل أبل، جوجل، رويترز) صغه كـ "سبق صحفي 🚨".
        2. إذا كان متداولاً كإشاعة، فنده بالمنطق صغه كـ "تفنيد إشاعة 🔍".
        3. اللغة: عربية بيضاء بسيطة (بدون تكلف لغوي).
        4. ركز على الفائدة العملية في الـ 24 ساعة القادمة.
        5. تجنب الهاشتاقات الكثيرة (واحد أو اثنين كافية).
        """

        # المحاولة الأولى: Gemini 2.0 Flash
        if self.gemini_key:
            try:
                print("🔍 جاري التحقق والصياغة عبر Gemini...")
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=fact_check_prompt
                )
                return self.clean_output(response.text)
            except Exception as e:
                print(f"⚠️ Gemini واجه ضغطاً: {e}")

        # المحاولة الثانية: Groq (Llama 3 70B)
        if self.groq_key:
            try:
                print("🚀 استخدام المحرك الاحتياطي Groq...")
                completion = self.groq_client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[{"role": "user", "content": fact_check_prompt}]
                )
                return self.clean_output(completion.choices[0].message.content)
            except Exception as e:
                print(f"❌ فشل جميع المحركات: {e}")
        
        return None

    def generate_smart_reply(self, mention_text, username):
        """توليد ردود ذكية ومختصرة جداً لمنع التكرار والإزعاج"""
        prompt = f"رد باختصار تقني ودود على المتابع {username} الذي يقول: {mention_text}. اجعل الرد مفيداً وقصيراً."
        
        try:
            # نفضل Gemini للردود لدقته في فهم السياق العربي
            res = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt
            )
            return self.clean_output(res.text)
        except:
            # رد محايد وسريع في حال تعطل الـ AI تماماً
            return f"أهلاً {username}، وجهة نظر تقنية مثيرة! سأقوم بمتابعة التحديثات حول هذا الأمر. 🛠️"
