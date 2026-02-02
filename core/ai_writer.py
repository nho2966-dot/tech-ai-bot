import openai

class AIWriter:
    def __init__(self):
        # سيتم جلب المفتاح تلقائياً من البيئة إذا تم ضبطه في السيكرتس
        self.client = openai.OpenAI()

    def generate_practical_content(self, news_item, content_type='tweet'):
        """توليد محتوى تقني بأسلوب بشري بسيط وقيمة عملية"""
        
        prompts = {
            'tweet': f"اشرح هذا الخبر ببساطة مع نصيحة عملية: {news_item['summary']}",
            'thread': f"حول هذا الخبر لثريد تعليمي بسيط يشرح الفائدة منه: {news_item['summary']}",
            'poll': f"اصنع استطلاع رأي ذكي بـ 4 خيارات حول هذا الخبر: {news_item['title']}",
            'security': f"حلل الخبر أمنياً وأعطِ نصيحة حماية سهلة: {news_item['summary']}",
            'tool': f"اشرح هذه الأداة التقنية وكيف توفر وقت المستخدم: {news_item['summary']}",
            'myth': f"صحح المفاهيم الخاطئة المتعلقة بهذا الخبر بأسلوب هادئ: {news_item['summary']}",
            'tips': f"أعطِ 3 نصائح سريعة وعملية بناءً على هذا التحديث: {news_item['summary']}"
        }

        prompt = prompts.get(content_type, prompts['tweet'])

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "أنت خبير تقني بأسلوب بشري بسيط جداً. ابتعد عن الرسميات، ركز على الفائدة، ولا تستخدم إيموجي بشكل مفرط. هدفك أن تبدو كصديق خبير ينصح صديقه."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    def generate_smart_reply(self, mention_text, username):
        """توليد رد ذكي وبسيط على المتابعين"""
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"رد على المتابع {username} بأسلوب تقني ودود وقصير جداً. إذا سأل سؤالاً أجبه ببساطة، وإذا شكرك رد بلطف."},
                {"role": "user", "content": mention_text}
            ]
        )
        return response.choices[0].message.content.strip()
