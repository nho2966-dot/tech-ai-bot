import openai
import random

class AIWriter:
    def __init__(self):
        self.client = openai.OpenAI()

    def generate(self, news_item, type='tweet'):
        system_instructions = (
            "أنت خبير تقني عالمي بأسلوب بشري بسيط جداً. "
            "ابتعد عن التكلف، ركز على 'الزبدة العملية' والفائدة للمستخدم. "
            "لا تستخدم كلمات روبوتية، تحدث كصديق خبير."
        )
        
        prompts = {
            'tweet': f"اشرح هذا الخبر ببساطة مع نصيحة عملية واحدة: {news_item}",
            'thread': f"حول هذا الخبر إلى ثريد (سلسلة تغريدات) تعليمي بسيط يشرح 'كيفية الاستفادة' منه خطوة بخطوة.",
            'poll': f"بناءً على {news_item}، اصنع استطلاع رأي ذكي وبسيط بـ 4 خيارات حول مستقبل هذه التقنية.",
            'security': f"حلل هذا الخبر أمنياً وأعطِ نصيحة حماية مباشرة وسهلة للتطبيق: {news_item}"
        }

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": prompts.get(type, prompts['tweet'])}
            ],
            temperature=0.6 # توازن بين الدقة والأسلوب البشري
        )
        return response.choices[0].message.content.strip()
