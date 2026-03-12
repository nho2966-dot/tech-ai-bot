name: AI Media Engine V150 - Technical Sovereignty

on:
  # 1. التشغيل التلقائي (يومياً الساعة 10 صباحاً بتوقيت عمان/مكة)
  schedule:
    - cron: '0 7 * * *' 
  
  # 2. التشغيل اليدوي من واجهة GitHub
  workflow_dispatch:
    inputs:
      run_mode:
        description: 'اختر وضع التشغيل'
        default: 'manual'
        required: true
        type: choice
        options:
          - manual
          - auto

jobs:
  run-tech-empire:
    runs-on: ubuntu-latest
    timeout-minutes: 120 # وقت كافٍ للبحث والتحليل والنشر

    steps:
      - name: 📂 Checkout Repository
        uses: actions/checkout@v4

      - name: 🐍 Set up Python 3.10
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          cache: 'pip'

      - name: 🛠️ Install FFmpeg (For Video Intelligence)
        run: |
          sudo apt-get update
          sudo apt-get install -y ffmpeg

      - name: 📦 Install Python Dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

      - name: 🚀 Launch V150 CTO Engine
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
          X_API_KEY: ${{ secrets.X_API_KEY }}
          X_API_SECRET: ${{ secrets.X_API_SECRET }}
          X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
          X_ACCESS_SECRET: ${{ secrets.X_ACCESS_SECRET }}
        # تشغيل يدوي أو تلقائي بناءً على المدخلات
        run: |
          python main.py ${{ github.event.inputs.run_mode || 'auto' }}

      - name: 💾 Persistence: Upload V150 Database
        if: always() # لضمان رفع قاعدة البيانات حتى لو فشل السكربت للتحليل
        uses: actions/upload-artifact@v4
        with:
          name: tech-sovereignty-v150-db
          path: tech_sovereignty_v150.db # تأكد أن هذا الاسم مطابق تماماً لما في main.py
          retention-days: 7 # الاحتفاظ بالملف لمدة أسبوع
