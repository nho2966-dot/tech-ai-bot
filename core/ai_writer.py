import os
from google import genai
try:
    from groq import Groq
except ImportError:
    pass # سيتم التعامل معها داخل الكود

class AIWriter:
    def __init__(self):
        # تحميل المفاتيح
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.groq_key = os.environ.get("GROQ_API_KEY") # خيار احتياطي
        
        # تهيئة العميل الأساسي (Gemini)
        if self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)
        
        # تهيئة العميل الاحتياطي (Groq)
        if self.groq_key:
            self.groq_client = Groq(api_key=self.groq_key)

    def generate_practical_content(self, news_item, content_type='tweet'):
        """النظام يحاول مع جيميناي، إذا فشل ينتقل لجروك"""
        instruction = "خبير تقني بأسلوب بشري بسيط. لغة بيضاء. لا تعقيد لغوي. ركز على القيمة العملية."
        prompt = f"{instruction}\n\n الموضوع: {news_item['summary']} \n نوع المحتوى: {content_type}"

        # المحاولة الأولى: Gemini 2.0 Flash (الأقوى والأحدث)
        if self.gemini_key:
            try:
                print("🪄 محاولة توليد المحتوى عبر Gemini...")
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                return response.text.strip()
            except Exception as e:
                print(f"⚠️ جيميناي واجه مشكلة: {e}")

        # المحاولة الثانية (الاحتياطية): Groq Llama 3 (السرعة القصوى)
        if self.groq_key:
            try:
                print("🚀 محاولة التوليد عبر الخيار الاحتياطي (Groq)...")
                completion = self.groq_client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[{"role": "user", "content": prompt}]
                )
                return completion.choices[0].message.content.strip()
            except Exception as e:
                print(f"❌ جميع خيارات الذكاء الاصطناعي فشلت: {e}")
        
        return "عذراً، المحرك حالياً خارج الخدمة."

    def generate_smart_reply(self, mention_text, username):
        """ردود ذكية مع نظام الفشل التلقائي (Fallback)"""
        prompt = f"رد باختصار وود كخبير تقني على {username}: {mention_text}"
        
        try:
            # محاولة جيميناي
            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt
            )
            return response.text.strip()
        except:
            # إذا فشل، جرب جروك فوراً
            try:
                completion = self.groq_client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "user", "content": prompt}]
                )
                return completion.choices[0].message.content.strip()
            except:
                return "شكراً لتفاعلك! سألقي نظرة وأرد عليك قريباً. 🛠️"
def analyze_and_verify(self, news_item):
        """تحليل الخبر وتفنيد ما إذا كان إشاعة أو حقيقة"""
        instruction = """
        بصفتك محققاً تقنيًا، حلل الخبر التالي:
        1. هل المصدر الأساسي موثوق؟
        2. هل هناك تناقضات منطقية؟
        3. إذا كان إشاعة، فندها بالأدلة التقنية.
        4. إذا كان حقيقة، صغها كسبق صحفي سريع.
        """
        
        prompt = f"{instruction}\n\nالخبر المرصود: {news_item['title']} - {news_item['summary']}"
        
        # نستخدم Gemini هنا لقدرته العالية على التحليل المنطقي
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return response.text.strip()
        except:
            return None # في حال الفشل ننتقل للمحرك الاحتياطي
