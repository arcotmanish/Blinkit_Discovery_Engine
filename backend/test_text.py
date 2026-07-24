import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.text import clean_text, count_words, hash_text, detect_language, chunk_review

def test():
    # 1. clean_text
    raw = "This is a <br> test!!! with   too many    spaces &amp; things!!!"
    cleaned = clean_text(raw)
    print(f"Cleaned: '{cleaned}'")
    assert cleaned == "This is a test! with too many spaces & things!"
    
    # 2. count_words
    c = count_words(cleaned)
    print(f"Word count: {c}")
    assert c == 10
    
    # 3. hash_text
    h = hash_text(cleaned)
    print(f"Hash: {h}")
    assert len(h) == 32
    
    # 4. detect_language
    lang = detect_language("This is a simple english text.")
    print(f"Lang: {lang}")
    assert lang == 'en'
    
    # 5. chunk_review
    short_text = "This is short."
    print("Chunks (short):", chunk_review(short_text))
    
    med_text = " ".join(["word"] * 100) + ". " + " ".join(["word"] * 50) + "."
    chunks_med = chunk_review(med_text)
    print(f"Chunks (medium - {len(med_text.split())} words): {len(chunks_med)}")
    
    long_text = " ".join(["sentence one."] * 20) + " " + " ".join(["sentence two."] * 20)
    chunks_long = chunk_review(long_text)
    print(f"Chunks (long - {len(long_text.split())} words): {len(chunks_long)}")
    
    print("All tests passed.")

if __name__ == '__main__':
    test()
