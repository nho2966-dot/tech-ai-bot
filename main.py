def _get_optimal_style(self, topic):
        """استخراج الأسلوب الذي حقق أعلى مكافأة تاريخياً لهذا الموضوع"""
        with sqlite3.connect(DB_FILE) as c:
            res = c.execute("""
                SELECT style FROM feedback 
                WHERE topic=? 
                ORDER BY reward DESC LIMIT 1
            """, (topic,)).fetchone()
        return res[0] if res else "Narrative Expert"

    def post_elite_scoop(self):
        """محرك النشر: جلب، فلترة، وصياغة نُخبوية"""
        if self._is_throttled("post", 90): return
        
        # تحديث بيانات التفاعل قبل اتخاذ قرار النشر الجديد
        self._update_feedback()
        
        all_entries = []
        for src in (self.sources + self.reddit_feeds):
            feed = feedparser.parse(src)
            all_entries.extend(feed.entries[:5])

        candidates = []
        for e in all_entries:
            text = (e.title + getattr(e, 'description', '')).lower()
            # تقييم النخبوية: التركيز على المسربات، المواصفات، وأدوات الأفراد
            score = sum(v for k, v in BASE_ELITE_SCORE.items() if re.search(rf"\b{k}\b", text))
            if score >= 3:
                candidates.append(e)

        if not candidates: return
        
        # اختيار السكوب الأقوى عشوائياً من بين النخبة
        target = random.choice(candidates)
        h = hashlib.sha256(target.title.encode()).hexdigest()

        with sqlite3.connect(DB_FILE) as c:
            if c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): return

            topic = "TECH" # يمكن تطوير المصنف لاحقاً
            style = self._get_optimal_style(topic)
            
            # بناء المهمة للـ Brain مع التركيز على التقسيمة الحماسية
            mission = f"صغ سكوب خليجي نخبوي بأسلوب {style}. ركز على فائدة الفرد القصوى."
            context = f"Title: {target.title}\nInfo: {getattr(target, 'description', target.link)}"
            
            content = self._brain(mission, context)
            
            if content:
                try:
                    # إضافة الـ RTL Mark لضمان هيبة النص من اليمين
                    final_text = f"{RTL_MARK}{content}"
                    self.x.create_tweet(text=final_text)
                    
                    c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "POST", datetime.now().isoformat()))
                    c.commit()
                    self._lock("post")
                    logging.info(f"🚀 Published: {target.title[:30]}...")
                except Exception as e:
                    logging.error(f"X Posting Error: {e}")

    def handle_mentions(self):
        """الرد الذكي مع Grounding لمنع الهلوسة"""
        if self._is_throttled("mentions", 15): return
        try:
            mentions = self.x.get_users_mentions(id=self.bot_id)
            if not mentions.data: return
            
            with sqlite3.connect(DB_FILE) as c:
                for t in mentions.data:
                    h = hashlib.sha256(f"reply_{t.id}".encode()).hexdigest()
                    if c.execute("SELECT 1 FROM memory WHERE h=?", (h,)).fetchone(): continue
                    
                    # الرد بذكاء خليجي نخبوي
                    reply_content = self._brain("رد نخبوي خليجي بيضاء مختصر جداً ومفيد.", t.text)
                    if reply_content:
                        self.x.create_tweet(text=f"{RTL_MARK}{reply_content}", in_reply_to_tweet_id=t.id)
                        c.execute("INSERT INTO memory VALUES (?,?,?)", (h, "REPLY", datetime.now().isoformat()))
                        c.commit()
        except Exception as e:
            logging.error(f"Mentions Error: {e}")

if __name__ == "__main__":
    bot = SovereignApexBotV101()
    # تشغيل المنظومة
    bot.handle_mentions()
    bot.post_elite_scoop()
