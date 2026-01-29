import json
import yaml
from core.trend_hunter import get_trending_topic
from core.ai_writer import generate_content
from core.tweet_optimizer import optimize
from core.publisher import publish
from utils.helpers import is_peak_time, choose_post_type
from utils.logger import log

with open("config.yaml") as f:
    config = yaml.safe_load(f)

with open("state.json") as f:
    state = json.load(f)

if not is_peak_time(config["posting"]["peak_hours"]):
    log("⏰ خارج وقت الذروة – تم التخطي")
    exit()

topic = get_trending_topic(state["last_topics"])
mode = choose_post_type() if config["posting"]["allow_threads"] else "tweet"

log(f"🔥 Topic: {topic}")
log(f"📝 Mode: {mode}")

content = generate_content(topic, mode)

if mode == "thread":
    content = [optimize(t) for t in content.split("\n") if t.strip()]
else:
    content = optimize(content)

publish(content)

state["last_topics"].append(topic)
state["last_topics"] = state["last_topics"][-10:]

with open("state.json", "w") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
