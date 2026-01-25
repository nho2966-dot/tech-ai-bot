name: TechAgent Pro - Run Bot

on:
  workflow_dispatch:
  schedule:
    - cron: '0 * * * *'   # كل ساعة
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build-and-run:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then
            pip install -r requirements.txt
          else
            echo "requirements.txt غير موجود → تثبيت الحزم يدوياً"
            pip install tweepy openai python-dotenv pyyaml requests
          fi

      - name: Debug - Show structure
        run: |
          echo "Current dir: $(pwd)"
          echo "GITHUB_WORKSPACE: $GITHUB_WORKSPACE"
          ls -la
          echo "Contents of tech-ai-bot folder:"
          ls -la tech-ai-bot || echo "مجلد tech-ai-bot غير موجود"

      - name: Change to bot directory & Run
        working-directory: ./tech-ai-bot
        env:
          CONFIG_YAML: ${{ secrets.CONFIG_YAML }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          X_BEARER_TOKEN: ${{ secrets.X_BEARER_TOKEN }}
          X_API_KEY: ${{ secrets.X_API_KEY }}
          X_API_SECRET: ${{ secrets.X_API_SECRET }}
          X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
          X_ACCESS_SECRET: ${{ secrets.X_ACCESS_SECRET }}
        run: |
          echo "Working directory: $(pwd)"
          ls -la
          python main.py

      - name: Upload logs (if any)
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: bot-logs
          path: |
            tech-ai-bot/*.log
            tech-ai-bot/botlog.txt
            tech-ai-bot/agent_logs.log
          retention-days: 7
