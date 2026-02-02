import openai

class AIWriter:
    def __init__(self):
        # تحميل مفتاح OpenAI من الـ Secrets
        self.client = openai.OpenAI()

    def generate_post(self, trend_data, prompt_path='prompts/tweet.txt'):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            expert_instructions = f.read()

        response = self.client.chat.completions.create(
            model="gpt-4o",  # استخدام موديل قوي لضمان الجودة
            messages=[
                {
                    "role": "system", 
                    "content": "You are a seasoned expert in technology content creation. Your output must be technically rigorous, accurate, and professional."
                },
                {
                    "role": "user", 
                    "content": f"{expert_instructions}\n\nسياق التريند الحالي:\n{trend_data}"
                }
            ],
            # بما أن لديك اشتراك X، يمكننا زيادة الطول قليلاً لضمان عدم نقص المحتوى
            max_tokens=800, 
            temperature=0.4 # درجة منخفضة لضمان الدقة التقنية بدلاً من الإبداع اللغوي
        )
        return response.choices[0].message.content.strip()
