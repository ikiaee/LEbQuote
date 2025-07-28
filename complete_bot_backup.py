import os
import random
import re
import sys
import json
import asyncio
import datetime
import requests
import subprocess
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode
from gtts import gTTS

# --- Load environment variables ---
load_dotenv(dotenv_path="/home/Kiaee0192/.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
bot = Bot(token=BOT_TOKEN)

# --- Path Configuration ---
QUOTES_PATH = "/home/Kiaee0192/quotes.txt"
VOCAB_PATH = "/home/Kiaee0192/vocab_bank.json"
POEM_PATH = "/home/Kiaee0192/poem_bank.json"
REPO_PATH = "/home/Kiaee0192/LEbQuote"
USED_QUOTES_PATH = "/home/Kiaee0192/used_quotes.json"
VIDEO_PATH = "/home/Kiaee0192/video_bank.json"

letters = ["A", "B", "C", "D"]

def clean_word(word):
    return word.strip('*').strip().lower()

def find_vocab_entry(word, vocab_bank):
    clean = clean_word(word)
    if clean in vocab_bank:
        return vocab_bank[clean]

    variations = [
        clean.rstrip('s'),
        clean.rstrip('es'),
        clean.rstrip('ing'),
        clean.rstrip('ed'),
        clean[:-3] + 'y' if clean.endswith('ies') else None,
        clean[:-1] + 'e' if clean.endswith('ing') else None
    ]

    for variation in filter(None, variations):
        if variation in vocab_bank:
            return vocab_bank[variation]
    return None

def process_quote(quote):
    print(f"\nDEBUG: Original quote: {quote}")  # Debug line
    telegram_quote = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", quote)
    print(f"DEBUG: Telegram quote: {telegram_quote}")  # Debug line
    github_quote = quote  # Keep original formatting
    print(f"DEBUG: GitHub quote: {github_quote}")  # Debug line
    return telegram_quote, github_quote

def load_quotes():
    with open(QUOTES_PATH, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def load_vocab():
    with open(VOCAB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_poems():
    with open(POEM_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_used_quotes():
    if os.path.exists(USED_QUOTES_PATH):
        with open(USED_QUOTES_PATH, "r") as f:
            return json.load(f)
    return []

def load_videos():
    if os.path.exists(VIDEO_PATH):
        with open(VIDEO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def generate_quiz(word, definition, vocab_bank):
    all_definitions = [v["definition"] for v in vocab_bank.values()]
    wrong_choices = random.sample(
        [d for d in all_definitions if d != definition], 3
    )
    options = wrong_choices + [definition]
    random.shuffle(options)
    return options, options.index(definition)

def generate_author_link(author):
    wiki_url = f"https://en.wikipedia.org/wiki/{author.replace(' ', '_')}"
    try:
        if requests.get(wiki_url).status_code == 200:
            return wiki_url
    except:
        pass
    return f"https://www.google.com/search?q={author.replace(' ', '+')}"

async def post_to_telegram(content_type, **kwargs):
    try:
        if content_type == "text":
            return await bot.send_message(
                chat_id=CHANNEL_ID,
                text=kwargs["text"],
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        elif content_type == "audio":
            with open(kwargs["filename"], "rb") as f:
                return await bot.send_audio(
                    chat_id=CHANNEL_ID,
                    audio=f,
                    caption=kwargs.get("caption"),
                    parse_mode=ParseMode.HTML,
                    title=kwargs.get("title"),
                    performer=kwargs.get("performer")
                )
    except Exception as e:
        print(f"Telegram posting failed: {e}")

async def git_operations():
    """Robust Git operations handler"""
    try:
        os.chdir(REPO_PATH)

        # Clean up any failed operations
        os.system("git rebase --abort >/dev/null 2>&1")
        os.system("git merge --abort >/dev/null 2>&1")

        # Handle unstaged changes
        status = os.popen("git status --porcelain").read().strip()
        if status:
            print("> Stashing local changes...")
            os.system("git stash push -m 'Auto-stash by bot' >/dev/null 2>&1")
            needs_pop = True
        else:
            needs_pop = False

        # Pull with rebase
        print("> Syncing with remote...")
        pull_status = os.system("git pull --rebase --quiet origin main")
        if pull_status != 0:
            raise Exception("Failed to sync with remote")

        # Restore stashed changes if needed
        if needs_pop:
            print("> Applying stashed changes...")
            os.system("git stash pop --quiet >/dev/null 2>&1")

        # Add and commit only if changes exist
        changed_files = os.popen("git status --porcelain").read().strip()
        if changed_files:
            print("> Committing changes...")
            os.system("git add . >/dev/null 2>&1")
            commit_msg = f"Update {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            os.system(f"git commit --quiet -m '{commit_msg}' >/dev/null 2>&1")

            # Push changes
            print("> Pushing to remote...")
            push_status = os.system("git push --quiet origin main >/dev/null 2>&1")
            if push_status != 0:
                raise Exception("Failed to push changes")

        print("✓ Git operations completed")
        return True

    except Exception as e:
        print(f"! Git error: {str(e)}")
        # Final cleanup
        os.system("git rebase --abort >/dev/null 2>&1")
        os.system("git merge --abort >/dev/null 2>&1")
        os.system("git reset --hard HEAD >/dev/null 2>&1")
        return False

async def update_index_page():
    """Regenerate index.html with all posts"""
    try:
        posts_dir = os.path.join(REPO_PATH, "posts")
        os.makedirs(posts_dir, exist_ok=True)

        # Get all posts sorted by date (newest first)
        all_posts = sorted(
            [f for f in os.listdir(posts_dir) if f.endswith('.html')],
            key=lambda x: os.path.getmtime(os.path.join(posts_dir, x)),
            reverse=True
        )

        # Generate posts list HTML
        posts_html = "\n".join(
            f'<li><a href="posts/{post}">{post.replace(".html", "").replace("_", " at ")}</a></li>'
            for post in all_posts
        )

        # Read template and insert posts
        with open(os.path.join(REPO_PATH, "index_template.html"), "r") as f:
            template = f.read()

        # Debug for INDEX template
        print("\nIndex Template Validation:")
        print(f"{'✓' if '<!-- POSTS_PLACEHOLDER -->' in template else '✗'} POSTS_PLACEHOLDER")

        with open(os.path.join(REPO_PATH, "index.html"), "w") as f:
            f.write(template.replace("<!-- POSTS_PLACEHOLDER -->", posts_html))

        print(f"✓ Updated index.html with {len(all_posts)} posts")
        return True
    except Exception as e:
        print(f"! Failed to update index: {e}")
        return False

async def git_cleanup():
    """Clean up git repository before operations"""
    try:
        os.chdir(REPO_PATH)
        # Reset any changes
        os.system("git reset --hard HEAD")
        # Clean untracked files
        os.system("git clean -fd")
        return True
    except Exception as e:
        print(f"! Git cleanup failed: {e}")
        return False

async def update_github_pages(quote_data, poem_data=None, video_data=None, is_historical=False):
    """Update GitHub Pages with new content"""
    try:
        # Verify we have quote data
        if not quote_data:
            raise ValueError("No quote data provided")

        print("\nDEBUG: Starting GitHub Pages Update")
        print(f"Received quote data: {json.dumps(quote_data, indent=2)}")

        # Set up paths and directories
        os.chdir(REPO_PATH)
        os.makedirs("posts", exist_ok=True)
        os.makedirs("audio", exist_ok=True)

        # Create timestamped filename
        # Handle dates for historical vs. new posts
        if is_historical and "date" in quote_data:
            now = quote_data["date"]  # Use original post date
        else:
            now = datetime.datetime.now()  # Use current time for new posts
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")
        post_filename = f"{date_str}_{time_str}.html"
        post_filepath = os.path.join(REPO_PATH, "posts", post_filename)

        # Get quote components
        original_quote = quote_data["original_quote"]  # With ** markers
        display_quote = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", original_quote)
        bold_words = quote_data["bold_words"]
        author = quote_data.get("author", "Unknown")

        print(f"\nDEBUG: Processing quote: {original_quote}")
        print(f"Bold words detected: {bold_words}")

        # Generate author link
        author_link_html = ""
        if author and author != "Unknown":
            link = generate_author_link(author)
            author_link_html = f'<a href="{link}" target="_blank">{author}</a>'
        else:
            author_link_html = author

        # Build quote section
        quote_section = f"""
<section class="quote-section">
    <h2>Quote of the Day</h2>
    <blockquote>{display_quote}</blockquote>
    <p class="author">— {author_link_html}</p>
</section>
"""

        # Process vocabulary
        vocab_html = ""
        vocab_bank = load_vocab()

        if not bold_words:
            vocab_html = """
<section class="quiz-box">
    <h3>Vocabulary Reflection</h3>
    <p>Today's quote doesn't contain specific vocabulary focus words.</p>
    <p>Reflect on the meaning and message of the quote itself.</p>
</section>
"""
        else:
            for word in bold_words:
                entry = find_vocab_entry(word, vocab_bank)
                if entry:
                    options, correct_idx = generate_quiz(word, entry["definition"], vocab_bank)
                    vocab_html += f"""
<section class="quiz-box">
    <h3>Vocabulary Focus: {word}</h3>
    <p><strong>Definition:</strong> {entry['definition']}</p>
    <div class="quiz">
        <p><strong>Quiz:</strong> What does <em>{word}</em> mean?</p>
        <ol type="A">
            <li>{options[0]}</li>
            <li>{options[1]}</li>
            <li>{options[2]}</li>
            <li>{options[3]}</li>
        </ol>
        <div class="answer">
            <strong>Answer:</strong> <span class="spoiler">{letters[correct_idx]}) {options[correct_idx]}</span>
        </div>
    </div>
</section>
"""
                else:
                    print(f"DEBUG: No vocabulary entry found for '{word}'")

        # Process poem if available
        poem_section = ""
        if poem_data:
            poem_title = poem_data.get("title", "Untitled")
            poem_author = poem_data.get("author", "")
            poem_lines = poem_data.get("lines", [])

            # Generate audio
            audio_filename = f"{poem_title.replace(' ', '_')}.mp3"
            audio_path = os.path.join(REPO_PATH, "audio", audio_filename)
            if not os.path.exists(audio_path):
                tts_text = "\n".join(poem_lines)
                tts = gTTS(text=tts_text, lang="en")
                tts.save(audio_path)

            # Build poem HTML
            author_html = ""
            if poem_author:
                author_link = generate_author_link(poem_author)
                author_html = f'<p class="author">by <a href="{author_link}" target="_blank">{poem_author}</a></p>'

            poem_body_html = "".join(f"<p>{line}</p>" for line in poem_lines)

            poem_section = f"""
<section class="poem-box">
    <h3>Poem of the Day: {poem_title}</h3>
    {author_html}
    <div class="poem-text">{poem_body_html}</div>
    <audio controls>
        <source src="../audio/{audio_filename}" type="audio/mpeg">
        Your browser does not support the audio element.
    </audio>
</section>
"""

        # Read template
        template_path = os.path.join(REPO_PATH, "post_template.html")
        with open(template_path, "r", encoding="utf-8") as f:
            template_html = f.read()

        # Validate template placeholders
        print("\nTemplate Validation:")
        required_placeholders = {
            "QUOTE_SECTION": quote_section,
            "VOCAB_QUIZ_SECTION": vocab_html,
            "POEM_SECTION": poem_section
        }

        for section, content in required_placeholders.items():
            placeholder = f"<!-- {section} -->"
            exists = placeholder in template_html
            print(f"{'✓' if exists else '✗'} {placeholder.ljust(20)} | "
                  f"Content: {'exists' if content else 'empty'}")

        # Generate final HTML
        final_html = (
            template_html
            .replace("{{DATE}}", now.strftime("%B %d, %Y"))
            .replace("{{YEAR}}", str(now.year))
            .replace("<!-- QUOTE_SECTION -->", quote_section)
            .replace("<!-- VOCAB_QUIZ_SECTION -->", vocab_html)
            .replace("<!-- POEM_SECTION -->", poem_section)
        )


        # Add historical post watermark (if applicable)
        if is_historical:
            historical_note = """
            <div class="historical-note">
                <p>🔍 Archived from Telegram on {date}</p>
            </div>
            """.format(date=datetime.datetime.now().strftime("%Y-%m-%d"))
            final_html = final_html.replace("<!-- HISTORICAL_MARKER -->", historical_note)

        # Save post file
        with open(post_filepath, "w", encoding="utf-8") as f:
            f.write(final_html)

        # Git operations
        subprocess.run(["git", "add", "."], cwd=REPO_PATH)
        commit_msg = f"Add daily post {date_str} {time_str}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_PATH)
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_PATH)

        # Update index page
        await update_index_page()

        # Trigger GitHub Pages rebuild
        print("\nTriggering GitHub Pages rebuild...")
        result = subprocess.run(
            ["curl", "-X", "POST",
             "https://api.github.com/repos/ikiaee/LEbQuote/pages/builds",
             "-H", f"Authorization: token {GITHUB_TOKEN}",
             "-H", "Accept: application/vnd.github.v3+json"],
            capture_output=True,
            text=True
        )
        print(f"Rebuild API response: {result.stdout}")

        print(f"\n✓ Successfully created GitHub Pages post: {post_filename}")
        return True

    except Exception as e:
        print(f"\n! Failed to update GitHub Pages: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        if hasattr(e, 'lineno'):
            print(f"Line number: {e.lineno}")
        return False

async def post_quote():
    """Post daily quote with vocabulary (Telegram and GitHub versions)"""
    try:
        # Load quotes and used quotes
        quotes = load_quotes()
        used_quotes = load_used_quotes()

        # Filter available quotes
        available_quotes = [q for q in quotes if q not in used_quotes]
        if not available_quotes:
            print("No new quotes available")
            return None, None

        # Select random quote
        quote = random.choice(available_quotes)
        used_quotes.append(quote)

        # Save updated used quotes
        with open(USED_QUOTES_PATH, "w") as f:
            json.dump(used_quotes, f)

        # Process quote versions
        telegram_quote = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", quote)  # Telegram format
        github_quote = quote  # Preserve original with ** for GitHub

        # Extract author
        author = None
        if "—" in quote:
            author = quote.split("—")[-1].strip()

        # Build Telegram message
        message = f"<b>Quote of the Day</b>\n\n{telegram_quote}"
        if author:
            message += f"\n\n— <b>{author}</b>"

        # Add vocabulary quizzes to Telegram
        vocab = load_vocab()
        bold_words = re.findall(r"\*\*(.*?)\*\*", quote)

        for word in bold_words:
            entry = find_vocab_entry(word, vocab)
            if entry:
                options, correct_idx = generate_quiz(word, entry["definition"], vocab)
                message += f"\n\n<b>Vocabulary Focus:</b> <i>{word}</i>\n{entry['definition']}\n\n<b>Quiz:</b> What does <i>{word}</i> mean?\n"
                for i, opt in enumerate(options):
                    message += f"{letters[i]}) {opt}\n"
                message += f"\nAnswer: <tg-spoiler>{letters[correct_idx]}) {options[correct_idx]}</tg-spoiler>"

        # Add author link if available
        if author:
            author_link = generate_author_link(author)
            message += f"\nLearn about the author: {author_link}"

        # Post to Telegram
        await post_to_telegram("text", text=message)

        # Prepare return data (for GitHub Pages)
        return_data = {
            "original_quote": quote,           # With ** markers
            "display_quote": github_quote,     # Same as original_quote
            "telegram_quote": telegram_quote,  # For debugging
            "author": author,
            "bold_words": bold_words           # Pre-extracted
        }

        return quote, return_data

    except Exception as e:
        print(f"Quote posting failed: {e}")
        return None, None

async def post_poem():
    """Post daily poem with audio"""
    try:
        poems = load_poems()
        if not poems:
            return None

        poem = random.choice(poems)
        poem_title = poem.get("title", "Untitled")
        poem_author = poem.get("author", "")
        poem_lines = poem.get("lines", [])

        # Build message
        message = f"<b>Poem of the Day</b>\n\n<b>{poem_title}</b>"
        if poem_author:
            message += f"\nby {poem_author}"
        message += "\n\n" + "\n".join(poem_lines[:4]) + "\n[...]"

        # Generate audio
        audio_dir = os.path.join(REPO_PATH, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        audio_file = os.path.join(audio_dir, f"{poem_title.replace(' ', '_')}.mp3")

        tts = gTTS("\n".join(poem_lines), lang="en")
        tts.save(audio_file)

        await post_to_telegram(
            "audio",
            filename=audio_file,
            caption=message,
            title=poem_title,
            performer=poem_author if poem_author else "Unknown"
        )

        return {
            "title": poem_title,
            "author": poem_author,
            "lines": poem_lines
        }

    except Exception as e:
        print(f"Poem posting failed: {e}")
        return None


async def archive_telegram_posts(limit=100):
    """NEW FUNCTION: Retrieve historical posts from Telegram"""
    try:
        posts = []
        async with bot:
            async for message in bot.get_chat_history(chat_id=CHANNEL_ID, limit=limit):
                if not (message.text or message.caption):
                    continue

                posts.append({
                    "date": message.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "content": message.text or message.caption,
                    "is_quote": "Quote of the Day" in (message.text or message.caption)
                })

        with open(f"{REPO_PATH}/telegram_archive.json", "w") as f:
            json.dump(posts, f)
        return posts

    except Exception as e:
        print(f"Archive error: {e}")
        return []

def process_historical_message(message):
    """NEW FUNCTION: Convert Telegram message to GitHub format"""
    try:
        if not message["is_quote"]:
            return None

        parts = message["content"].split("\n\n")
        quote_text = parts[1] if len(parts) > 1 else ""
        author = parts[2].replace("— ", "").strip() if len(parts) > 2 else None

        return {
            "original_quote": quote_text,
            "author": author,
            "date": datetime.datetime.strptime(message["date"], "%Y-%m-%d %H:%M:%S"),  # Keep this
            "bold_words": re.findall(r"\*\*(.*?)\*\*", quote_text),
            "is_historical": True  # Add this flag
        }

    except Exception as e:
        print(f"Process error: {e}")
        return None

async def restore_history(limit=50):
    """NEW FUNCTION: Restore posts safely"""
    print(f"Restoring last {limit} posts...")
    archived = await archive_telegram_posts(limit)

    restored = 0
    for msg in archived:
        quote_data = process_historical_message(msg)
        if not quote_data:
            continue

        try:
            await update_github_pages(quote_data, is_historical=True)
            restored += 1
            await asyncio.sleep(3)  # Rate limiting
        except Exception as e:
            print(f"Failed to restore {quote_data.get('date')}: {e}")

    print(f"Restored {restored}/{len(archived)} posts")
    return restored

async def post_daily_content():
    try:
        print("Starting daily content posting...")

        # 0. Cleanup first
        await git_cleanup()

        # 1. Sync with Git
        if not await git_operations():
            raise Exception("Initial sync failed")

        # 2. Post to Telegram
        quote, quote_data = await post_quote()
        poem_data = await post_poem()

        if not quote_data:
            raise Exception("No quote data to post")

        # 3. Update GitHub Pages
        if not await update_github_pages(quote_data, poem_data):
            raise Exception("GitHub Pages update failed")

        # 4. Wait a bit for GitHub to process
        await asyncio.sleep(10)

        # 5. Final sync and verification
        if not await git_operations():
            raise Exception("Final sync failed")

        print("✓ Daily posting completed")
        return True

    except Exception as e:
        print(f"! Posting failed: {e}")
        return False

async def main():
    """Modified main function with optional restoration"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--restore', type=int, help='Number of historical posts to restore')
    args = parser.parse_args()

    if args.restore:
        await restore_history(args.restore)
    else:
        await post_daily_content()  # Original working flow

if __name__ == "__main__":
    asyncio.run(main())
