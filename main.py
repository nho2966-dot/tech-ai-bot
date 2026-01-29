import os
import json
import time
import logging
import tweepy
import yaml
from openai import OpenAI
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")

class TechExpertProFinal:
    def __init__(self):
        logging.info("--- Tech Expert Pro [Ultra Path Finder] ---")
        
        # 1. البحث الديناميكي الشامل عن config.yaml
        config_name = "config.yaml"
        selected_path = None
        
        # البحث في المجلد الحالي، المجلد الأب، والجذر
        search_locations = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), config_name),
            os.path.join(os.getcwd(), config_name),
            os.path.abspath(config_name)
        ]
        
        for p in search_locations:
            if os.path.exists(p):
                selected_path = p
                break
        
        if not selected_path:
            logging.error("❌ لم يتم العثور على config.yaml. سأقوم بطباعة كافة الملفات المتاحة المساعدة:")
            for root, dirs, files in os.walk(os.getcwd()):
                for file in files:
                    logging.info(f"📂 Found file: {os.path.join(root, file)}")
            raise FileNotFoundError("config.yaml is missing from the repository structure!")

        logging.info(f"✅ تم العثور على الإعدادات في: {selected_path}")
        with open(selected_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
