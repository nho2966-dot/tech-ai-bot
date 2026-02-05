def _ai_judge_and_enhance(self, raw_draft, mode):
        judge_prompt = (
            "أنت خبير تقني خليجي ومدقق جودة (Premium Quality). راجع النص التالي:\n"
            "1. حوّل اللغة إلى لهجة خليجية بيضاء كأنك تسولف مع ربعك.\n"
            "2. ضروري جداً تضع مصطلحين تقنيين بالإنجليزية على الأقل بين قوسين (مثال: (Edge Computing)).\n"
            "3. إذا كان المحتوى دسم ومفيد، عطه درجة 5/5.\n"
            "4. ركز على إن النص يكون طويل ومفصل لأن الحساب Premium.\n"
            "في النهاية اذكر السكور بهذا الشكل الضبط: [SCORE: 5/5]"
        )
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct", # موديل دقيق جداً في التنفيذ
                messages=[{"role": "system", "content": judge_prompt}, {"role": "user", "content": raw_draft}],
                temperature=0.4
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"⚠️ خطأ في التدقيق: {e}")
            return None
