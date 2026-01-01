fetch('../logs/bot.log')
  .then(res => res.text())
  .then(data => document.getElementById('log-content').textContent = data || 'لا توجد سجلات.')
  .catch(err => document.getElementById('log-content').textContent = '❌ خطأ: ' + err.message);