# استخدام نسخة بايثون مستقرة وخفيفة
FROM python:3.10-slim

# ضبط منطقة التوقيت (مهم جداً للـ ROI والتقارير)
ENV TZ=Asia/Riyadh
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# تثبيت الاعتمادات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود وقاعدة البيانات
COPY . .

# إنشاء ملف اللوج لضمان صلاحيات الكتابة
RUN touch system_sovereign.log

# تشغيل البوت
CMD ["python", "main.py"]
