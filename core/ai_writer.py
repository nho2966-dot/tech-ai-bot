import os
import requests

API_URL = "https://openrouter.ai/api/v1/chat/completions"

def generate_content(topic, mode="tweet"):
    prompt_file = "prompts/tweet.txt" if mode == "tweet" else "prompts/thread.txt"

    with open(prompt_file, encoding="utf-8") as f:
        prompt = f.read().replace("{{topic}}", topic)

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-4.1-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8
        }
    )

    return response.json()["choices"][0]["message"]["content"]
