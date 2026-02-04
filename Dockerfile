FROM python:3.10-slim

# ضبط التوقيت (مهم جداً لتحليل الـ ROI)
ENV TZ=Asia/Riyadh
RUN apt-get update && apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# تثبيت الاعتمادات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY . .

# التشغيل
CMD ["python", "main.py"]
