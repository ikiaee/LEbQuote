import json
import os
import re
from datetime import datetime
from pathlib import Path

BASE_URL = ""  # Empty string for docs-based publishing

# ===== CONFIGURATION =====
INPUT_JSON = "result.json"  # Now looks in same directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "docs")
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
    """Improved quote component extraction"""
    components = {
        "quote": "",
        "author": "Unknown",
        "vocabulary": {
            "word": "",
            "definition": ""
        },
        "quiz": {
            "question": "",
            "options": [],
            "answer": ""
        }
    }

    # Extract quote and author (improved regex)
    quote_match = re.search(r'(?:"|“)(.*?)(?:"|”)(?:\s*[—–]\s*)(.*?)(?:\n|$)', full_text)
    if quote_match:
        components["quote"] = quote_match.group(1).strip()
        author = quote_match.group(2).strip()

        # Handle author links
        author_link_match = re.search(r'\[(.*?)\]\((.*?)\)', author)
        if author_link_match:
            components["author"] = f'<a href="{author_link_match.group(2)}">{author_link_match.group(1)}</a>'
        else:
            components["author"] = author

    # Improved vocabulary extraction
    vocab_match = re.search(r"Vocabulary Focus:\s*([^\n]+)\n([^\n]+)", full_text)
    if vocab_match:
        components["vocabulary"]["word"] = vocab_match.group(1).strip('*').strip()
        components["vocabulary"]["definition"] = vocab_match.group(2).strip()

    ## Improved quiz extraction
    quiz_match = re.search(r"What does (.*?) mean\?(.*?)Answer:\s*(.*?)(?:\n|$)", full_text, re.DOTALL)
    if quiz_match:
        components["vocabulary"]["word"] = quiz_match.group(1).strip('*').strip()  # Store in components
        options_text = quiz_match.group(2).strip()
        # Improved options splitting that handles A), B) format correctly
        components["quiz"]["options"] = [
            opt.strip()
            for opt in re.split(r'\b[A-Z]\)', options_text)  # \b ensures we match whole words
            if opt.strip()
        ]
        components["quiz"]["answer"] = quiz_match.group(3).strip()

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
    """Improved quote saving with better quiz handling"""
    full_text = flatten_text(msg.get('text', ''))
    data = extract_quote_components(full_text)

    if not data['quote']:
        return False

    # Generate vocabulary section only if we have both word and definition
    vocab_html = ""
    if data['vocabulary']['word'] and data['vocabulary']['definition']:
        vocab_html = f"""
        <div class="vocab-section">
            <h2>Vocabulary Focus: {data['vocabulary']['word']}</h2>
            <p>{data['vocabulary']['definition']}</p>
        </div>
        """

    # Generate quiz section only if we have all components
    quiz_html = ""
    if (data['vocabulary']['word'] and
        data['quiz']['options'] and
        data['quiz']['answer']):

        # Fixed options_html generation with proper parenthesis closing
        options_html = "".join([
            f'<div class="quiz-option">{chr(65+i)}) {opt}</div>'
            for i, opt in enumerate(data['quiz']['options'][:4])  # Limit to 4 options
        ])  # This closing square bracket was missing

        quiz_html = f"""
        <div class="quiz-section">
            <h3>Quiz</h3>
            <p>What does <em>{data['vocabulary']['word']}</em> mean?</p>
            <div class="quiz-options">
                {options_html}
            </div>
            <details class="quiz-answer">
                <summary>Show Answer</summary>
                <p>{data['quiz']['answer']}</p>
            </details>
        </div>
        """

    # Create safe filename
    safe_author = re.sub(r'[^\w\s-]', '', data['author']).strip().replace(" ", "_")
    filename = f"{date}_{safe_author[:50]}.html"

    # Generate HTML content
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Quote: {data['quote'][:50]}...</title>
    <link rel="stylesheet" href="../styles2.css">
</head>
<body>
    <div class="container">
        <h1>Quote of the Day</h1>

        <div class="quote-box">
            <blockquote>"{data['quote']}"</blockquote>
            <div class="author">— {data['author']}</div>
        </div>

        {vocab_html}
        {quiz_html}
    </div>
</body>
</html>"""

    with open(os.path.join(QUOTES_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(html_content)
    return True

def save_poem(msg, date):
    full_text = flatten_text(msg.get('text', ''))
    data = extract_poem_components(full_text)

    if not data['content']:
        return False

    safe_title = re.sub(r'[^\w\s-]', '', data['title']).strip()
    filename = f"{date}_{safe_title[:50]}.html"

    # Generate media HTML (fixed version)
    media_html = ''
    if 'file' in msg:
        audio_path = f"/LEbQuote/media_files/{os.path.basename(msg.get('file', ''))}"
        media_html = f'''
        <div class="media-section">
            <h2>Audio Version</h2>
            <audio controls>
                <source src="{audio_path}" type="audio/mpeg">
                Your browser does not support audio
            </audio>
            <p><a href="{audio_path}" download>Download Audio</a></p>
        </div>'''

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Poem: {data['title']}</title>
    <link rel="stylesheet" href="../styles2.css">
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

        {media_html}

    </div>
</body>
</html>"""

    with open(os.path.join(POEMS_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(html_content)
    return True
def generate_index(quotes, poems):
    post_links = []

    # Process quotes - REMOVED date filtering
    for quote_file in os.listdir(QUOTES_DIR):
        if quote_file.endswith('.html'):
            date_str = quote_file.split('_')[0]
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                post_links.append((date_obj, f"quotes/{quote_file}", "Quote"))
            except ValueError:
                continue

    # Sort by date (newest first)
    post_links.sort(key=lambda x: x[0], reverse=True)

    # Generate HTML list items
    list_items = []
    for date_obj, path, post_type in post_links:
        date_str = date_obj.strftime('%Y-%m-%d')  # Format date consistently
        list_items.append(f"""
        <li>
            <a href="{BASE_URL}{path}">
                <span class="timestamp">{date_str}</span>
                <span class="post-type">{post_type}</span>
            </a>
        </li>
        """)

    # Update index.html
    index_path = os.path.join(OUTPUT_DIR, 'index.html')
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()

    updated_content = content.replace(
        '<!-- List items remain the same but will display in reverse -->',
        '\n'.join(list_items)
    )

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

def main():
    try:
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return

    quote_count = 0

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
            # Poem processing completely removed
        except Exception as e:
            print(f"⚠️ Error processing message {msg.get('id')}: {e}")

    # Only pass quote_count to generate_index
    generate_index(quote_count, 0)  # Second argument (poem_count) set to 0

    print(f"\n📊 Processing Complete:")
    print(f"✅ Quotes saved: {quote_count}")
    print(f"📂 Output folder:")
    print(f"   - Quotes: {os.path.abspath(QUOTES_DIR)}")

if __name__ == "__main__":
    main()