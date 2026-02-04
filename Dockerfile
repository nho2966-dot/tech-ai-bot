FROM python:3.10-slim

# ضبط التوقيت لضمان دقة تقارير ROI
ENV TZ=Asia/Riyadh
RUN apt-get update && apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# تثبيت المكتبات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ ملفات المشروع
COPY . .

# تشغيل النظام
CMD ["python", "main.py"]
