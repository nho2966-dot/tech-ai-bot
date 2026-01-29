from datetime import datetime
import random

def is_peak_time(peak_hours):
    return datetime.now().hour in peak_hours

def choose_post_type():
    return random.choice(["tweet", "thread"])
