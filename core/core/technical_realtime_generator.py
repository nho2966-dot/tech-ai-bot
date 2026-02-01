# -*- coding: utf-8 -*-
from typing import Dict, List, Optional
import json
import datetime
import random
from pathlib import Path

class TechnicalRealtimeGenerator:
    """
    محرك توليد تغريدات تقنية حية (عاجلة + تحليل + تفاعل)
    """
    
    def __init__(self, prompts_path="prompts/technical_realtime_posts_ar.txt"):
        self.prompts = self._load_prompts(prompts_path)
        self.sources = [
            "NVIDIA Blog", "OpenAI Blog", "Google AI Blog", "TechCrunch",
            "The Verge", "Reuters", "Nature", "Bloomberg"
        ]
    
    def _load_prompts(self, path: str) -> Dict[str, str]:
        """تحميل القوالب من ملف txt"""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # تقسيم القوالب حسب العنوان
        templates = {}
        current_template = ""
        for line in content.splitlines():
            if line.startswith("##"):
                current_template = line.strip()[3:]
                templates[current_template] = ""
            else:
                if current_template:
                    templates[current_template] += line + "\n"
        
        return templates
    
    def generate_post(self, news_item: Dict) -> Dict[str, str]:
        """توليد تغريدة تقنية حية بناءً على نوع الخبر"""
        
        topic = self._detect_topic(news_item["title"])
        template = self._select_template(topic)
        
        # استبدال المتغيرات في القالب
        filled = template.replace("[عنوان الخبر]", news_item["title"])
        filled = filled.replace("[الشركة]", news_item.get("company", "شركة غير معروفة"))
        filled = filled.replace("[المرض]", news_item.get("disease", "مرض غير معروف"))
        filled = filled.replace("[النسبة]", news_item.get("accuracy", "98%"))
        filled = filled.replace("[المدينة]", news_item.get("city", "مدينة غير معروفة"))
        filled = filled.replace("[المنظمة]", news_item.get("organization", "منظمة غير معروفة"))
        filled = filled.replace("[الاسم]", news_item.get("platform_name", "منصة غير معروفة"))
        filled = filled.replace("[الشركة]", news_item.get("company", "شركة غير معروفة"))
        
        # إضافة المصادر
        sources = random.sample(self.sources, 2)
        filled = filled.replace("[المصدر الرئيسي]", sources[0])
        filled = filled.replace("[المصدر الثانوي]", sources[1])
        
        # إضافة التاريخ
        now = datetime.datetime.now()
        filled = filled.replace("[تاريخ النشر]", now.strftime("%Y-%m-%d %H:%M UTC"))
        
        # إضافة الفوائد التقنية
        benefits = {
            "ai_model": ["تحسين فهم السياق بنسبة 40%", "دعم 100 لغة جديدة", "تكامل مباشر مع التطبيقات"],
            "hardware": ["تدريب أسرع بـ5x", "استهلاك طاقة أقل بنسبة 30%", "دعم لتقنيات مثل 3D AI"],
            "medical": ["تشخيص أسرع، وعلاج مبكر", "تقليل الأخطاء البشرية", "توفير وقت ومال للمرضى"],
            "autonomous_vehicle": ["تقليل حوادث الطرق بنسبة 70%", "قيادة آمنة حتى أثناء النوم", "استعمال الوقت في العمل أو الاسترخاء"],
            "robotic_kitchen": ["طعام مخصص لاحتياجاتك الغذائية", "تقليل الفاقد الغذائي", "تجربة طعام فريدة بدون تدخل بشري"],
            "smart_home": ["تكييف يضبط درجة الحرارة حسب مزاجك", "إنارة تتوافق مع دورة نومك", "كهرباء أقل بنسبة 40%"],
            "brain_computer": ["تحذيرك من الإجهاد قبل أن تشعر به", "تقديم نصائح نفسية بناءً على حالتك", "تحسين أداءك المهني والشخصي"],
            "environment": ["تخطيط أفضل للزراعة والري", "إنقاذ الغابات قبل اندلاع الحرائق", "تقليل الكوارث الطبيعية"],
            "education": ["تعلم ما تحتاجه فقط، وليس ما يفرض عليك", "تقدم أسرع في المواد التي تتفوق فيها", "تقليل التوتر والضغط الدراسي"],
            "automation": ["تقليل الوقت المستغرق في الكتابة بـ80%", "التركيز على الإبداع وليس التكرار", "زيادة الإنتاجية بشكل كبير"]
        }
        
        benefit_list = benefits.get(topic, ["فائدة تقنية 1", "فائدة تقنية 2", "فائدة تقنية 3"])
        filled = filled.replace("[فوائد تقنية 1]", benefit_list[0])
        filled = filled.replace("[فوائد تقنية 2]", benefit_list[1])
        filled = filled.replace("[فوائد تقنية 3]", benefit_list[2])
        
        # إضافة التحليل العميق
        deep_insights = {
            "ai_model": "هذه التقنية ليست مجرد تحسن، بل قد تُغير مسار صناعة الذكاء الاصطناعي في 2026.",
            "hardware": "القيمة الحقيقية لن تتضح فورًا، بل عند تبنّي هذه التقنية على نطاق واسع.",
            "medical": "التحدي الحقيقي ليس في الدقة، بل في التوزيع العادل لهذه التقنية.",
            "autonomous_vehicle": "الانتقال إلى السيارات الذكية سيكون تحوّلًا اجتماعيًا كبيرًا، وليس تقنيًا فقط.",
            "robotic_kitchen": "الروبوتات لا تحل مكان البشر، بل تُعزز قدراتهم.",
            "smart_home": "المنازل الذكية ستكون أكثر من مجرد أجهزة — بل将成为 مستقبل الحياة المنزلية.",
            "brain_computer": "الحدود بين الإنسان والآلة ستتلاشى مع تقدم هذه التقنية.",
            "environment": "التكنولوجيا يمكن أن تكون الحل، لكنها أيضًا قد تصبح المشكلة إذا لم تُستخدم بمسؤولية.",
            "education": "التعليم الذكي قد يُعيد تعريف التعليم العالمي، لكنه يحتاج إلى تنظيم حكيم.",
            "automation": "الأتمتة ليست خطرًا، بل فرصة لرفع الإنتاجية والإبداع."
        }
        
        filled = filled.replace("[تحليل عميق وتقني]", deep_insights.get(topic, "تحليل تقني عميق"))
        
        # إضافة السؤال التفاعلي
        questions = {
            "ai_model": "هل تتوقع أن تستخدم هذا النموذج في مشروعك القادم؟",
            "hardware": "هل تعتقد أن البنية التحتية الحالية جاهزة لاستيعاب هذه الشرائح؟",
            "medical": "هل تعتقد أن هذه التقنية يجب أن تكون مجانية للجميع؟",
            "autonomous_vehicle": "ما هو أول شيء ستقوم به داخل السيارة الذكية؟",
            "robotic_kitchen": "هل تأكل في مطعم آلي؟ أم تفضل البشر؟",
            "smart_home": "ما هي أول شيء تريد أن يكون ذكيًا في منزلك؟",
            "brain_computer": "هل تثق بأن أي تطبيق يمكن أن يفهمك؟",
            "environment": "هل تعتقد أن التكنولوجيا يمكن أن تحل مشكلات البيئة؟",
            "education": "هل ترغب أن يُعلّمك الذكاء الاصطناعي؟",
            "automation": "هل تستخدم أدوات الذكاء الاصطناعي في عملك؟"
        }
        
        filled = filled.replace("[سؤال تفاعلي ذكي]", questions.get(topic, "ما رأيك في هذا التطور؟"))
        
        return {
            "text": filled,
            "topic": topic,
            "source": sources[0],
            "timestamp": now.isoformat()
        }
    
    def _detect_topic(self, title: str) -> str:
        """تحديد الموضوع التقني من العنوان"""
        title_lower = title.lower()
        if any(k in title_lower for k in ["gpt", "llm", "model", "ai"]):
            return "ai_model"
        elif any(k in title_lower for k in ["chip", "gpu", "hardware", "shriha"]):
            return "hardware"
        elif any(k in title_lower for k in ["cancer", "diagnosis", "medical"]):
            return "medical"
        elif any(k in title_lower for k in ["car", "vehicle", "drive"]):
            return "autonomous_vehicle"
        elif any(k in title_lower for k in ["kitchen", "food", "robotic"]):
            return "robotic_kitchen"
        elif any(k in title_lower for k in ["home", "house", "smart"]):
            return "smart_home"
        elif any(k in title_lower for k in ["brain", "mind", "neural"]):
            return "brain_computer"
        elif any(k in title_lower for k in ["environment", "climate", "satellite"]):
            return "environment"
        elif any(k in title_lower for k in ["education", "learn", "school"]):
            return "education"
        elif any(k in title_lower for k in ["automation", "write", "content"]):
            return "automation"
        return "ai_model"
    
    def _select_template(self, topic: str) -> str:
        """اختيار قالب حسب الموضوع"""
        template_map = {
            "ai_model": "قالب 2: نموذج جديد",
            "hardware": "قالب 1: شريحة جديدة",
            "medical": "قالب 3: نظام طبي",
            "autonomous_vehicle": "قالب 4: سيارة ذكية",
            "robotic_kitchen": "قالب 5: مطعم آلي",
            "smart_home": "قالب 6: منزل ذكي",
            "brain_computer": "قالب 7: تطبيق ذكاء اصطناعي",
            "environment": "قالب 8: تقنية بيئة",
            "education": "قالب 9: منصة تعليمية",
            "automation": "قالب 10: أتمتة تسويقية"
        }
        
        template_name = template_map.get(topic, "قالب 1: شريحة جديدة")
        return self.prompts[template_name]
