from google import genai
import os
try:
    from groq import Groq
except ImportError:
    pass

class AIWriter:
    def __init__(self):
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.groq_key = os.environ.get("GROQ_API_KEY")
        
        if self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)
        if self.groq_key:
            self.groq_client = Groq(api_key=self.groq_key)

    def verify_and_generate(self, news_item):
        """رصد السبق وتفنيد الإشاعات بذكاء اصطناعي مزدوج"""
        
        # برومبت متخصص للتحقق (Fact-Checking)
        fact_check_prompt = f"""
        بصفتك خبيراً تقنياً ومحققاً في الأخبار العاجلة:
        الخبر: {news_item['title']}
        المحتوى: {news_item['summary']}
        
        المهمة:
        1. إذا كان الخبر من مصدر رسمي (أبل، جوجل، سامسونج، رويترز) صغه كـ "سبق صحفي 🚨".
        2. إذا كان الخبر متداولاً كإشاعة غير مؤكدة، فندها بناءً على المنطق التقني صغه كـ "تفنيد إشاعة 🔍".
        3. اجعل الأسلوب بشرياً بسيطاً (لغة بيضاء) بعيداً عن التكلف.
        4. ركز على ما سيحدث خلال الـ 24 ساعة القادمة.
        """

        # المحاولة الأولى: Gemini (للتحليل العميق والتفنيد)
        if self.gemini_key:
            try:
                print("🔍 جاري التحقق من الخبر عبر Gemini...")
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=fact_check_prompt
                )
                return response.text.strip()
            except Exception as e:
                print(f"⚠️ تنبيه: Gemini واجه ضغطاً، الانتقال للمحرك الاحتياطي: {e}")

        # المحاولة الثانية: Groq (للسرعة في حال تعطل Gemini)
        if self.groq_key:
            try:
                print("🚀 صياغة السبق الصحفي عبر المحرك الاحتياطي...")
                completion = self.groq_client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[{"role": "user", "content": fact_check_prompt}]
                )
                return completion.choices[0].message.content.strip()
            except Exception as e:
                print(f"❌ فشل المحركين في التحقق: {e}")
        
        return None

    def generate_smart_reply(self, mention_text, username):
        """ردود ذكية استهدافية"""
        prompt = f"رد باختصار وذكاء تقني على {username} بخصوص: {mention_text}"
        try:
            # محاولة الرد عبر أسرع موديل متاح لضمان السبق في التفاعل
            res = self.gemini_client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return res.text.strip()
        except:
            return "نقطة مثيرة للاهتمام! سأتابع المستجدات وأوافيك بالجديد. 🛠️"
