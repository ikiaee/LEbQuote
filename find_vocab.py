from bs4 import BeautifulSoup
import re

# UPDATE THIS PATH TO YOUR ACTUAL FILE
MESSAGE_FILE = "C:/Users/kiaee/Desktop/1/ChatExport_2025-07-02/messages.html"

def analyze_messages():
    with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    
    total_messages = 0
    vocab_messages = []
    
    for msg in soup.find_all("div", class_="message"):
        total_messages += 1
        text = msg.get_text().replace("\n", " ").strip()
        
        # Check for any vocabulary indicators
        is_vocab = ("word:" in text.lower() or "vocab:" in text.lower()) and ("definition" in text.lower() or "meaning" in text.lower())
        
        if is_vocab:
            vocab_messages.append(text[:150])  # Store first 150 chars
    
    print(f"Total messages: {total_messages}")
    print(f"Potential vocabulary posts: {len(vocab_messages)}")
    print("\nSample vocabulary posts:")
    for i, post in enumerate(vocab_messages[:5]):
        print(f"{i+1}. {post}...")

if __name__ == "__main__":
    analyze_messages()