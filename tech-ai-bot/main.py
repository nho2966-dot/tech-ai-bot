name: Unified Tech Bot

on:
  schedule:
    - cron: '*/20 * * * *'  # للردود (كل 20 دقيقة)
    - cron: '0 */6 * * *'    # للنشر (كل 6 ساعات)
  workflow_dispatch:
  push:
    branches: [ main ]

jobs:
  run:
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
          pip install -r requirements.txt

      - name: Run Unified Bot
        env:
          GEMINI_KEY: ${{ secrets.GEMINI_KEY }}
          TAVILY_KEY: ${{ secrets.TAVILY_KEY }}
          X_API_KEY: ${{ secrets.X_API_KEY }}
          X_API_SECRET: ${{ secrets.X_API_SECRET }}
          X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
          X_ACCESS_TOKEN_SECRET: ${{ secrets.X_ACCESS_TOKEN_SECRET }} # توحيد الاسم هنا
          BOT_USERNAME: ${{ vars.BOT_USERNAME }}
        run: |
          # التشغيل من المجلد الرئيسي لضمان رؤية المجلدات الفرعية
          python src/main.py
