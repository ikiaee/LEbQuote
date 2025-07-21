import json
import os
import re
from datetime import datetime
from pathlib import Path

BASE_URL = "/LEbQuote/"  # ← Add this line

# ===== CONFIGURATION =====
INPUT_JSON = "result.json"  # Now looks in same directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
QUOTES_DIR = os.path.join(OUTPUT_DIR, "quotes")
POEMS_DIR = os.path.join(OUTPUT_DIR, "poems")
MEDIA_DIR = os.path.join(OUTPUT_DIR, "media")

# Ensure output directories exist
Path(QUOTES_DIR).mkdir(parents=True, exist_ok=True)
Path(POEMS_DIR).mkdir(parents=True, exist_ok=True)
Path(MEDIA_DIR).mkdir(parents=True, exist_ok=True)

def flatten_text(msg_text):
    """Convert Telegram's formatted text array into plain text with preserved links"""
    if isinstance(msg_text, str):
        return msg_text

    plain_text = []
    for segment in msg_text:
        if isinstance(segment, dict):
            if segment.get('type') == 'text_link':
                plain_text.append(f"[{segment.get('text', '')}]({segment.get('href', '')})")
            else:
                plain_text.append(segment.get('text', ''))
        else:
            plain_text.append(str(segment))
    return ''.join(plain_text).strip()

def is_quote_message(msg):
    """Check if message contains a quote"""
    if msg.get('type') != 'message':
        return False

    text = flatten_text(msg.get('text', ''))
    return any(marker in text for marker in [
        "Daily Quote",
        "Quote of the Day",
        "📖",
        "Vocabulary Focus:"
    ])

def is_poem_message(msg):
    """Check if message contains a poem"""
    if msg.get('type') != 'message':
        return False

    text = flatten_text(msg.get('text', ''))
    return "Poem of the Day" in text or "poem" in text.lower()

def extract_quote_components(full_text):
    """Extract quote components with author links"""
    # Extract quote and author (with potential markdown link)
    quote_match = re.search(r'"(.*?)"(?:\s*—|\s*–)(.*?)(?:\n|$)', full_text)
    quote = quote_match.group(1).strip() if quote_match else ""

    # Handle author with potential markdown link
    author = quote_match.group(2).strip() if quote_match else "Unknown"
    author_link_match = re.search(r'\[(.*?)\]\((.*?)\)', author)
    if author_link_match:
        author_name = author_link_match.group(1)
        author_link = author_link_match.group(2)
        author = f'<a href="{author_link}" target="_blank">{author_name}</a>'

    # Extract vocabulary
    vocab_match = re.search(r"Vocabulary Focus:\s*(.*?)\n(.*?)(?:\n\n|\nQuiz:|$)", full_text, re.DOTALL)
    vocab_word = vocab_match.group(1).strip() if vocab_match else ""
    vocab_def = vocab_match.group(2).strip() if vocab_match else ""

    # Extract quiz
    quiz_match = re.search(r"What does (.*?) mean\?(.*?)Answer:\s*(.*?)(?:\n|$)", full_text, re.DOTALL)
    quiz_question = quiz_match.group(2).strip() if quiz_match else ""
    quiz_answer = quiz_match.group(3).strip() if quiz_match else ""

    return {
        "quote": quote,
        "author": author,
        "vocabulary": {
            "word": vocab_word,
            "definition": vocab_def
        },
        "quiz": {
            "question": quiz_question,
            "answer": quiz_answer
        }
    }

def extract_poem_components(full_text):
    """Extract poem components"""
    clean_text = re.sub(r'^.*?Poem of the Day\s*\n', '', full_text, flags=re.DOTALL)

    title_match = re.match(r'^(.*?)\nby (.*?)\n', clean_text)
    if title_match:
        title = title_match.group(1).strip()
        author = title_match.group(2).strip()

        # Handle author links
        author_link_match = re.search(r'\[(.*?)\]\((.*?)\)', author)
        if author_link_match:
            author_name = author_link_match.group(1)
            author_link = author_link_match.group(2)
            author = f'<a href="{author_link}" target="_blank">{author_name}</a>'

        content = clean_text[title_match.end():].strip()
    else:
        title = "Untitled"
        author = "Unknown"
        content = clean_text.strip()

    return {
        "title": title,
        "author": author,
        "content": content
    }

def save_quote(msg, date):
    """Save quote as properly formatted HTML"""
    full_text = flatten_text(msg.get('text', ''))
    data = extract_quote_components(full_text)

    if not data['quote']:
        return False

    # Create safe filename
    safe_author = re.sub(r'[^\w\s-]', '', data['author']).strip()
    filename = f"{date}_{safe_author[:50]}.html"

    # Generate HTML content
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Quote: {data['quote'][:50]}...</title>
    <link rel="stylesheet" href="{BASE_URL}styles2.css">
</head>
<body>
    <div class="container">
        <h1>Quote of the Day</h1>

        <div class="quote-box">
            <blockquote>"{data['quote']}"</blockquote>
            <div class="author">— {data['author']}</div>
        </div>

        <div class="vocab-section">
            <h2>Vocabulary Focus</h2>
            <p><strong>{data['vocabulary']['word']}</strong><br>
            {data['vocabulary']['definition']}</p>
        </div>

        <div class="quiz-section">
            <h2>Quiz</h2>
            <p>What does {data['vocabulary']['word']} mean?</p>
            {data['quiz']['question']}
            <details>
                <summary>Show Answer</summary>
                <div class="answer">{data['quiz']['answer']}</div>
            </details>
        </div>

        <div class="historical-note">
            Originally posted on {date} •
            <a href="https://t.me/c/{msg.get('from_id', '').replace('channel', '')}/{msg.get('id', '')}" target="_blank">View original</a>
        </div>
    </div>
</body>
</html>"""

    with open(os.path.join(QUOTES_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(html_content)
    return True

def save_poem(msg, date):
    """Save poem as properly formatted HTML with audio"""
    full_text = flatten_text(msg.get('text', ''))
    data = extract_poem_components(full_text)

    if not data['content']:
        return False

    # Create safe filename
    safe_title = re.sub(r'[^\w\s-]', '', data['title']).strip()
    filename = f"{date}_{safe_title[:50]}.html"

    # Generate HTML content
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Poem: {data['title']}</title>
    <link rel="stylesheet" href="{BASE_URL}styles2.css">
</head>
<body>
    <div class="container">
        <h1>Poem of the Day</h1>

        <div class="poem-box">
            <h2>{data['title']}</h2>
            <div class="poem-author">by {data['author']}</div>
            <div class="poem-text">
                {data['content']}
            </div>
        </div>

        '<div class="media-section"><h2>Audio Version</h2><audio controls><source src="{BASE_URL}{msg.get('file', '')}" type="audio/mpeg">Your browser does not support audio</audio></div>'

        <div class="historical-note">
            Originally posted on {date} •
            <a href="https://t.me/c/{msg.get('from_id', '').replace('channel', '')}/{msg.get('id', '')}" target="_blank">View original</a>
        </div>
    </div>
</body>
</html>"""

    with open(os.path.join(POEMS_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(html_content)
    return True

def main():
    try:
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return

    quote_count = 0
    poem_count = 0

    for msg in data.get('messages', []):
        date_str = msg.get('date', '')
        try:
            date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").strftime('%Y-%m-%d')
        except:
            date = "1970-01-01"

        try:
            if is_quote_message(msg):
                if save_quote(msg, date):
                    quote_count += 1
            elif is_poem_message(msg):
                if save_poem(msg, date):
                    poem_count += 1

        except Exception as e:
            print(f"⚠️ Error processing message {msg.get('id')}: {e}")

    print(f"\n📊 Processing Complete:")
    print(f"✅ Quotes saved: {quote_count}")
    print(f"✅ Poems saved: {poem_count}")
    print(f"📂 Output folders:")
    print(f"   - Quotes: {os.path.abspath(QUOTES_DIR)}")
    print(f"   - Poems: {os.path.abspath(POEMS_DIR)}")

if __name__ == "__main__":
    main()