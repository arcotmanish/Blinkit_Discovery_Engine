import re
import hashlib
from typing import List
from langdetect import detect, LangDetectException

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode basic HTML entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    # Remove excessive punctuation repetition
    text = re.sub(r'([!?.])\1{2,}', r'\1', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def count_words(text: str) -> int:
    if not text:
        return 0
    return len(text.split())

def hash_text(text: str) -> str:
    normalized = re.sub(r'\s+', ' ', text).strip().lower()
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()

def detect_language(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"

def chunk_review(text: str) -> List[str]:
    words = text.split()
    word_count = len(words)
    
    if word_count < 60:
        return [text]
        
    sentences = re.split(r'(?<=[.!?])\s+', text)
    # Clean empty sentences that might result from split
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return [text]
        
    if word_count <= 200:
        midpoint = max(1, len(sentences) // 2)
        chunk1 = " ".join(sentences[:midpoint]).strip()
        chunk2 = " ".join(sentences[midpoint:]).strip()
        return [c for c in (chunk1, chunk2) if c]
        
    chunks = []
    current_chunk = []
    current_words = 0
    
    for sentence in sentences:
        sentence_words = len(sentence.split())
        if current_words + sentence_words > 120 and current_chunk:
            chunks.append(" ".join(current_chunk).strip())
            current_chunk = [sentence]
            current_words = sentence_words
        else:
            current_chunk.append(sentence)
            current_words += sentence_words
            
    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())
        
    return chunks
