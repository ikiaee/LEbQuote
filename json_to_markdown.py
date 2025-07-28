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
    """Convert Telegram's formatted text array into plain text with Markdown-style formatting"""
    if msg_text is None:
        return ""

    if isinstance(msg_text, str):
        return msg_text

    if not isinstance(msg_text, (list, dict)):
        return str(msg_text)

    plain_text = []

    # Handle both single dict and list of dicts
    segments = msg_text if isinstance(msg_text, list) else [msg_text]

    for segment in segments:
        if not isinstance(segment, dict):
            plain_text.append(str(segment))
            continue

        text = segment.get('text', '')
        if not text:
            continue

        # Apply Markdown-style formatting
        if segment.get('type') == 'bold':
            text = f"**{text}**"
        elif segment.get('type') == 'italic':
            text = f"_{text}_"

        plain_text.append(text)

    return ''.join(plain_text).strip()

def is_quote_message(text):
    """Detect quotes using multiple patterns"""
    patterns = [
        r'Quote of the Day.*?"(.*?)"[^"]*(—|–|by)(.*?)(\n|$)',
        r'"(.*?)"[^"]*(—|–|by)(.*?)(\n|$)',
        r'📖.*?\n(.*?)\n(—|–|by)(.*?)(\n|$)'
    ]

    text = text.replace('\n', ' ')
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    # Check for quote markers
    has_quote_markers = any(
        marker in text
        for marker in ["Quote of the Day", "Daily Quote", "📖"]
    )

    # Check for quote structure (text followed by author)
    has_quote_structure = re.search(r'".*?"\s*[—–-]\s*.+', text)

    return has_quote_markers or has_quote_structure

def is_poem_message(msg):
    """Check if message contains a poem"""
    if msg.get('type') != 'message':
        return False

    text = flatten_text(msg.get('text', ''))
    return "Poem of the Day" in text or "poem" in text.lower()

def extract_quote_components(full_text):
    """Extract components from formatted quote text"""
    if not full_text:
        return None

    # Convert to plain text first if needed
    if not isinstance(full_text, str):
        full_text = flatten_text(full_text)

    components = {
        "quote": "",
        "author": "Unknown",
        "vocabulary": [],
        "quiz": None
    }

    # Extract quote and author
    quote_match = re.search(r'"(.*?)"(?:\s*[—–-]\s*)(.*?)(?:\n|$)', full_text)
    if quote_match:
        components["quote"] = quote_match.group(1).strip()
        components["author"] = quote_match.group(2).strip()

    # Extract vocabulary words (bold text)
    components["vocabulary"] = re.findall(r'\*\*(.*?)\*\*', full_text)

    # Extract quiz if present
    quiz_match = re.search(r'Quiz: What does (.*?) mean\?(.*?)Answer:\s*(.*?)(?:\n|$)', full_text, re.DOTALL)
    if quiz_match:
        components["quiz"] = {
            "word": quiz_match.group(1).strip(),
            "options": [opt.strip() for opt in re.split(r'\s*[A-Z]\)\s*', quiz_match.group(2)) if opt.strip()],
            "answer": quiz_match.group(3).strip()
        }

    return components

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

def save_quote(msg, date, text):
    """Save quote as properly formatted HTML with vocabulary"""
    components = extract_quote_components(text)
    if not components or not components.get('quote'):
        print("🛑 Invalid quote components")
        return False

    # Create safe filename
    safe_author = re.sub(r'[^\w\s-]', '', components['author']).strip().replace(" ", "_")
    filename = f"{date}_{safe_author[:50]}.html"

    # Generate vocabulary section
    vocab_html = ""
    if components['vocabulary']:
        vocab_items = "\n".join(
            f"<li><strong>{word}</strong></li>"
            for word in components['vocabulary']
        )
        vocab_html = f"""
        <div class="vocab-section">
            <h2>Vocabulary Focus</h2>
            <ul>{vocab_items}</ul>
        </div>
        """

    # Generate quiz section if available
    quiz_html = ""
    if components.get('quiz'):
        options_html = "\n".join(
            f"<li>{opt}</li>"
            for opt in components['quiz']['options'][:4]  # Limit to 4 options
        )
        quiz_html = f"""
        <div class="quiz-section">
            <h3>Quiz</h3>
            <p>What does <em>{components['quiz']['word']}</em> mean?</p>
            <ol type="A">{options_html}</ol>
            <details>
                <summary>Show Answer</summary>
                <p>{components['quiz']['answer']}</p>
            </details>
        </div>
        """

    # Generate HTML content
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Quote: {components['quote'][:50]}...</title>
    <link rel="stylesheet" href="../styles2.css">
</head>
<body>
    <div class="container">
        <h1>Quote of the Day</h1>
        <p class="subtitle">Learn English By Quotes and Wisdom</p>
        <div class="quote-box">
            <blockquote>"{components['quote']}"</blockquote>
            <div class="author">— {components['author']}</div>
        </div>

        {vocab_html}
        {quiz_html}
    </div>
</body>
</html>"""

    # Ensure output directory exists
    os.makedirs(QUOTES_DIR, exist_ok=True)

    # Save file
    with open(os.path.join(QUOTES_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"💾 Saved quote to {filename}")
    return True

def save_poem(msg, date):
    full_text = flatten_text(msg.get('text', ''))
    data = extract_poem_components(full_text)

    if not data['content']:
        return False

    safe_title = re.sub(r'[^\w\s-]', '', data['title']).strip()
    filename = f"{date}_{safe_title[:50]}.html"

    # Generate media HTML
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

    # Build HTML content
    html_content = f"""
<html>
<head>
    <title>Poem: {data['title']}</title>
    <link rel="stylesheet" href="../styles2.css">
</head>
<body>
    <div class="container">
        <h1>Poem of the Day</h1>
        <p class="subtitle">Learn English By Quotes and Wisdom</p>
        <p style="color: #666; font-style: italic;">Learn English By Quotes and Wisdom</p>

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


def process_messages(data):
    quote_count = 0
    error_count = 0

    for i, msg in enumerate(data.get('messages', [])):
        try:
            # Skip if not a proper message dictionary
            if not isinstance(msg, dict) or 'text' not in msg:
                continue

            # Safely extract and flatten text
            text = safe_extract_text(msg)
            if not text:
                continue

            # Parse date safely
            date = safe_parse_date(msg.get('date'))

            # Check if this is a quote message
            if is_quote_message(text):
                print(f"\n🔍 Processing potential quote (Message {i}):")
                print(text[:200] + ("..." if len(text) > 200 else ""))

                if save_quote(msg, date, text):
                    quote_count += 1
                    print("✅ Saved quote successfully")

        except Exception as e:
            error_count += 1
            print(f"⚠️ Error in message {i}: {str(e)}")
            continue

    return quote_count, error_count

def safe_extract_text(msg):
    """Completely safe text extraction"""
    if not isinstance(msg, dict):
        return ""

    text = msg.get('text')
    if text is None:
        return ""

    if isinstance(text, str):
        return text.strip()

    if isinstance(text, list):
        return " ".join(str(item) for item in text if item)

    return str(text)

def safe_parse_date(date_str):
    """
    Safe date parsing with fallback"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").strftime('%Y-%m-%d')
    except:
        return "1970-01-01"

def main():
    print("🚀 Starting quote processing...")

    try:
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"📦 Loaded JSON with {len(data.get('messages', []))} messages")
    except Exception as e:
        print(f"❌ Failed to load JSON: {e}")
        return

    quote_count, error_count = process_messages(data)

    print("\n📊 Final Report:")
    print(f"🔢 Total messages: {len(data.get('messages', []))}")
    print(f"✅ Quotes saved: {quote_count}")
    print(f"⚠️ Errors encountered: {error_count}")
    print(f"📁 Output directory: {os.path.abspath(QUOTES_DIR)}")

    if quote_count == 0:
        print("\n🔴 No quotes were saved. Possible issues:")
        print("- Message format doesn't match expected patterns")
        print("- No valid quote messages in the JSON file")
        print("- Check sample messages with the debug output")


if __name__ == "__main__":
    main()