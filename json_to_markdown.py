import json
import os
import re
from datetime import datetime
from pathlib import Path

# ===== CONFIGURATION =====
INPUT_JSON = r"C:\Users\kiaee\Desktop\1\ChatExport_2025-07-20\result.json"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
QUOTES_DIR = os.path.join(OUTPUT_DIR, "quotes")
POEMS_DIR = os.path.join(OUTPUT_DIR, "poems")
MEDIA_DIR = os.path.join(OUTPUT_DIR, "media")  # New directory for videos/photos

def flatten_text(msg_text):
    """Convert Telegram's formatted text array into plain text"""
    if isinstance(msg_text, str):
        return msg_text
        
    plain_text = []
    for segment in msg_text:
        if isinstance(segment, dict):
            # Handle author links when they appear as text entities
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

def is_media_message(msg):
    """Check if message contains media (video/photo)"""
    return msg.get('type') == 'message' and ('file' in msg or 'photo' in msg)

def extract_quote_components(full_text):
    """Extract quote, author, vocabulary and quiz from text"""
    # Extract quote and author (with potential link)
    quote_match = re.search(r'"(.*?)"(?:\s*—|\s*–)(.*?)(?:\n|$)', full_text)
    quote = quote_match.group(1).strip() if quote_match else ""
    
    # Handle author with potential markdown link
    author = quote_match.group(2).strip() if quote_match else "Unknown"
    author_link_match = re.search(r'\[(.*?)\]\((.*?)\)', author)
    if author_link_match:
        author = f"[{author_link_match.group(1)}]({author_link_match.group(2)})"
    
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
        },
        "full_text": full_text
    }

def extract_poem_components(full_text):
    """Extract poem title and content"""
    clean_text = re.sub(r'^.*?Poem of the Day\s*\n', '', full_text, flags=re.DOTALL)
    
    title_match = re.match(r'^(.*?)\nby (.*?)\n', clean_text)
    if title_match:
        title = title_match.group(1).strip()
        author = title_match.group(2).strip()
        
        # Handle author links in poems
        author_link_match = re.search(r'\[(.*?)\]\((.*?)\)', author)
        if author_link_match:
            author = f"[{author_link_match.group(1)}]({author_link_match.group(2)})"
            
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

def save_media(msg, date):
    """Save video/photo messages to Markdown with media reference"""
    media_type = "video" if 'file' in msg else "photo"
    filename = f"{date}_{msg.get('id', '')}_{media_type}.md"
    
    # Generate media reference
    media_content = ""
    if media_type == "video":
        media_content = f"""
[Video: {msg.get('file_name', '')}]({msg.get('file', '')})
Duration: {msg.get('duration_seconds', 0)} seconds
Resolution: {msg.get('width', 0)}x{msg.get('height', 0)}
"""
    elif media_type == "photo":
        media_content = f"""
![Photo]({msg.get('photo', '')})
Resolution: {msg.get('width', 0)}x{msg.get('height', 0)}
"""
    
    # Generate Markdown content
    md_content = f"""---
title: "{msg.get('text', 'Media Content')[:50]}..."
date: {date}
media_type: {media_type}
---

{flatten_text(msg.get('text', ''))}

{media_content}

[View original](https://t.me/c/{msg.get('from_id', '').replace('channel', '')}/{msg.get('id', '')})
"""
    with open(os.path.join(MEDIA_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(md_content)
    return True

def save_quote(msg, date):
    """Save quote message to Markdown file"""
    full_text = flatten_text(msg.get('text', ''))
    data = extract_quote_components(full_text)
    
    if not data['quote']:
        return False
        
    # Create safe filename
    safe_author = re.sub(r'[^\w\s-]', '', data['author']).strip()
    filename = f"{date}_{safe_author[:50]}.md"
    
    # Generate Markdown content
    md_content = f"""---
title: "{data['quote'][:50]}..."
date: {date}
author: "{data['author']}"
---

> {data['quote']}
> — {data['author']}

## Vocabulary
**{data['vocabulary']['word']}**  
{data['vocabulary']['definition']}

## Quiz
{data['quiz']['question']}

<details>
<summary>Answer</summary>
{data['quiz']['answer']}
</details>

[View original](https://t.me/c/{msg.get('from_id', '').replace('channel', '')}/{msg.get('id', '')})
"""
    with open(os.path.join(QUOTES_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(md_content)
    return True

def save_poem(msg, date):
    """Save poem message to Markdown file"""
    full_text = flatten_text(msg.get('text', ''))
    data = extract_poem_components(full_text)
    
    if not data['content']:
        return False
        
    # Create safe filename
    safe_title = re.sub(r'[^\w\s-]', '', data['title']).strip()
    filename = f"{date}_{safe_title[:50]}.md"
    
    # Generate Markdown content
    md_content = f"""---
title: "{data['title']}"
date: {date}
author: "{data['author']}"
---

{data['content']}

[View original](https://t.me/c/{msg.get('from_id', '').replace('channel', '')}/{msg.get('id', '')})
"""
    # Handle media files
    if 'file' in msg:  # Audio
        md_content += f"\n\n[Audio: {msg.get('file_name', '')}]({msg.get('file', '')})"
    elif 'photo' in msg:  # Photo
        md_content += f"\n\n![Photo]({msg.get('photo', '')})"
    
    with open(os.path.join(POEMS_DIR, filename), 'w', encoding='utf-8') as f:
        f.write(md_content)
    return True

def main():
    # Create output folders
    Path(QUOTES_DIR).mkdir(parents=True, exist_ok=True)
    Path(POEMS_DIR).mkdir(parents=True, exist_ok=True)
    Path(MEDIA_DIR).mkdir(parents=True, exist_ok=True)  # New media folder

    try:
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return

    quote_count = 0
    poem_count = 0
    media_count = 0
    total_messages = len(data.get('messages', []))
    
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
            elif is_media_message(msg):
                if save_media(msg, date):
                    media_count += 1
                    
        except Exception as e:
            print(f"⚠️ Error processing message {msg.get('id')}: {e}")

    print(f"\n📊 Processing Complete:")
    print(f"✅ Quotes saved: {quote_count}")
    print(f"✅ Poems saved: {poem_count}")
    print(f"✅ Media files saved: {media_count}")
    print(f"📂 Output folders:")
    print(f"   - Quotes: {os.path.abspath(QUOTES_DIR)}")
    print(f"   - Poems: {os.path.abspath(POEMS_DIR)}")
    print(f"   - Media: {os.path.abspath(MEDIA_DIR)}")

if __name__ == "__main__":
    main()