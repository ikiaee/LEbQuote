from datetime import datetime

# Simulated Telegram content
latest_message = "❤️ Love is patient. Love is kind."

html_content = f"""
<html>
<head><title>Telegram Quotes</title></head>
<body>
  <h1>Latest Telegram Post</h1>
  <p>{latest_message}</p>
  <small>Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small>
  <br><br>
  <a href="https://t.me/YOUR_CHANNEL">Join our Telegram channel</a>
</body>
</html>
"""

with open("index.html", "w") as file:
    file.write(html_content)

print("HTML updated.")