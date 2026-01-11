name: Unified Tech Bot

on:
  # التشغيل التلقائي كل 20 دقيقة للردود، وكل 6 ساعات للنشر
  schedule:
    - cron: '*/20 * * * *'  # للردود
    - cron: '0 */6 * * *'    # للنشر التلقائي
  # السماح بالتشغيل اليدوي
  workflow_dispatch:
  # التشغيل عند دفع الكود
  push:
    branches: [ main ]

jobs:
  run-bot:
    runs-on: ubuntu-latest

    steps:
      # 1. استنساخ الكود من المستودع
      - name: Checkout Code
        uses: actions/checkout@v4

      # 2. تهيئة بيئة بايثون
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      # 3. تثبيت المكتبات المطلوبة
      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      # 4. تشغيل البوت الموحد
      - name: Run Unified Bot
        env:
          # ربط الأسرار المخزنة في إعدادات GitHub بمتغيرات البيئة
          GEMINI_KEY: ${{ secrets.GEMINI_KEY }}
          TAVILY_KEY: ${{ secrets.TAVILY_KEY }}
          X_API_KEY: ${{ secrets.X_API_KEY }}
          X_API_SECRET: ${{ secrets.X_API_SECRET }}
          X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
          X_ACCESS_TOKEN_SECRET: ${{ secrets.X_ACCESS_TOKEN_SECRET }}
          X_BEARER_TOKEN: ${{ secrets.X_BEARER_TOKEN }}
          BOT_USERNAME: ${{ vars.BOT_USERNAME }}
        run: |
          # تشغيل الملف الرئيسي الموجود في الجذر (Root)
          python main.py

      # 5. حفظ السجلات (اختياري) لرؤية النتائج في GitHub
      - name: Upload Logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: bot-logs
          path: logs/
