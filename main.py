# --- تابع: نشر الاستطلاع وحفظه ---
    def _post_poll(self, question, options, topic, reply_to):
        try:
            res = self.x.create_tweet(
                text=question[:280],
                in_reply_to_tweet_id=reply_to,
                poll_options=options[:4],
                poll_duration_minutes=1440
            )
            if res:
                poll_id = res.data["id"]
                expires = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

                with sqlite3.connect(DB_FILE) as conn:
                    # 1. حفظ الاستطلاع للمتابعة والتحليل لاحقاً
                    conn.execute("INSERT INTO active_polls VALUES (?, ?, ?, 0)", (poll_id, topic, expires))
                    # 2. تسجيل الاستطلاع في نظام قياس التفاعل (ROI)
                    self._register_roi(poll_id, topic, "POLL")
                
                logging.info(f"✅ تم نشر استطلاع حقيقي عن: {topic}")
                return poll_id
        except Exception as e:
            logging.error(f"❌ خطأ في نشر الاستطلاع: {e}")
            return None

    # --- 📊 تحليل الاستطلاعات المنتهية والبناء عليها ---
    def process_and_analyze_polls(self):
        logging.info("⚙️ فحص الاستطلاعات المكتملة لتحليلها...")
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(DB_FILE) as conn:
            polls = conn.execute("SELECT tweet_id, topic FROM active_polls WHERE expires_at < ? AND processed = 0", (now,)).fetchall()
        
        for p_id, topic in polls:
            try:
                # 1. جلب النتيجة من API تويتر
                tweet_data = self.x.get_tweet(p_id, expansions="attachments.poll_ids", tweet_fields="public_metrics")
                if 'polls' not in tweet_data.includes: continue
                
                poll = tweet_data.includes['polls'][0]
                winner = max(poll['options'], key=lambda x: x['votes'])
                total_votes = sum(option['votes'] for option in poll['options'])

                # 2. تحديث الـ ROI بعدد الأصوات
                self._update_roi_metrics(p_id, poll_votes=total_votes)

                # 3. توليد تحليل استراتيجي بناءً على الفائز (الممارسة التطبيقية)
                analysis = self._generate_ai_analysis(winner['label'], topic)
                
                if analysis:
                    msg = f"📢 بناءً على تصويتكم (الخيار الفائز: {winner['label']}):\n\n{analysis}"
                    self.x.create_tweet(text=msg[:280], in_reply_to_tweet_id=p_id)
                    
                    with sqlite3.connect(DB_FILE) as conn:
                        conn.execute("UPDATE active_polls SET processed = 1 WHERE tweet_id = ?", (p_id,))
                    logging.info(f"✅ تم نشر تحليل الاستطلاع لـ {topic}")

            except Exception as e:
                logging.error(f"❌ فشل تحليل الاستطلاع {p_id}: {e}")

    # --- 📈 نظام قياس وتحديث ROI ---
    def _update_roi_metrics(self, tweet_id, poll_votes=0):
        try:
            # جلب التفاعل الفعلي (Likes/Retweets) من X
            metrics = self.x.get_tweet(tweet_id, tweet_fields="public_metrics").data['public_metrics']
            
            score = (metrics['like_count'] * ROI_WEIGHTS['like'] +
                     metrics['retweet_count'] * ROI_WEIGHTS['repost'] +
                     metrics['reply_count'] * ROI_WEIGHTS['reply'] +
                     poll_votes * ROI_WEIGHTS['poll_vote'])

            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("""
                    UPDATE roi_metrics SET 
                    likes = ?, reposts = ?, replies = ?, poll_votes = ?, score = ?
                    WHERE tweet_id = ?
                """, (metrics['like_count'], metrics['retweet_count'], metrics['reply_count'], poll_votes, score, tweet_id))
        except: pass

    def _generate_ai_analysis(self, winner, topic):
        prompt = ANALYSIS_PROMPT.format(winner=winner)
        try:
            r = self.ai.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": f"الموضوع: {topic}"}]
            )
            return r.choices[0].message.content
        except: return None
