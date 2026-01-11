name: Unified Tech Bot

on:
  schedule:
    # تشغيل كل 20 دقيقة للردود
    - cron: '*/20 * * * *'
    # تشغيل كل 6 ساعات للنشر
    - cron: '0 */6 * * *'
  workflow_dispatch:
  push:
    branches: [ main ]

jobs:
  run-bot:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

      - name: Run Unified Bot
        env:
          # تم مطابقة هذه الأسماء بدقة مع الصورة التي أرفقتها لـ Repository Secrets
          GEMINI_KEY: ${{ secrets.GEMINI_KEY }}
          TAVILY_KEY: ${{ secrets.TAVILY_KEY }}
          X_API_KEY: ${{ secrets.X_API_KEY }}
          X_API_SECRET: ${{ secrets.X_API_SECRET }}
          X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
          X_ACCESS_TOKEN_SECRET: ${{ secrets.X_ACCESS_SECRET }} # لاحظ هنا ربطنا Secret الخاص بك بالاسم الذي يتوقعه الكود
          X_BEARER_TOKEN: ${{ secrets.X_BEARER_TOKEN }}
          # أضفنا أسرار تليجرام أيضاً لأنها تظهر في صورتك
          TG_TOKEN: ${{ secrets.TG_TOKEN }}
          TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}
          BOT_USERNAME: ${{ vars.BOT_USERNAME }}
        run: |
          # تشغيل main.py الموجود في المجلد الرئيسي (Root) كما يظهر في صورتك
          python main.py

      - name: Upload Logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: bot-logs
          path: logs/
