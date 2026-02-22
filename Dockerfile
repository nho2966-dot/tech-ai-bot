# 1. استخدام نسخة بايثون مستقرة وخفيفة لعام 2026
FROM python:3.11-slim

# 2. تحديد مجلد العمل داخل الحاوية
WORKDIR /app

# 3. تثبيت أدوات النظام الضرورية
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. نسخ ملف المتطلبات وتثبيت المكتبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. نسخ بقية ملفات المشروع (main.py, data, prompts, etc.)
COPY . .

# 6. إنشاء مجلد البيانات واللوجز إذا لم تكن موجودة لضمان عمل الذاكرة
RUN mkdir -p data logs

# 7. فتح المنفذ البرمجي (المتوافق مع كود Quart)
EXPOSE 8443

# 8. تشغيل المحرك الرئيسي باستخدام uvicorn للأداء العالي
CMD ["python", "main.py"]
