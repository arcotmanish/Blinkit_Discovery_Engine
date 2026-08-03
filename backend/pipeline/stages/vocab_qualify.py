import os
import asyncio
import string
import re
from db.client import supabase

class BehaviourVocabulary:
    def __init__(self, filepath: str):
        self.phrase_weight = 0
        self.verb_weight = 0
        self.object_weight = 0
        
        # Efficient in-memory lookup structures
        self.phrases = set()
        self.verbs = set()
        self.objects = set()
        
        self._load(filepath)
        
    def _load(self, filepath: str):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Vocabulary file not found at {filepath}")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Parse weights
            if line.startswith("phrase_weight:"):
                self.phrase_weight = int(line.split(":")[1].strip())
            elif line.startswith("verb_weight:"):
                self.verb_weight = int(line.split(":")[1].strip())
            elif line.startswith("object_weight:"):
                self.object_weight = int(line.split(":")[1].strip())
                
            # Parse sections
            elif line.startswith("## Phrases"):
                current_section = "phrases"
            elif line.startswith("## Verbs"):
                current_section = "verbs"
            elif line.startswith("## Objects"):
                current_section = "objects"
                
            # Parse list items
            elif line.startswith("- ") and current_section:
                item = line[2:].strip().lower()
                if current_section == "phrases":
                    self.phrases.add(item)
                elif current_section == "verbs":
                    self.verbs.add(item)
                elif current_section == "objects":
                    self.objects.add(item)

# Instantiate once when module is loaded (app startup)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
VOCAB_FILE = os.path.join(_PROJECT_ROOT, "Antigravity_Runtime_Vocabulary_v1.md")

vocab = BehaviourVocabulary(VOCAB_FILE)

def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def run_stage_vocab_qualify(run_id: str):
    print(f"Starting Behaviour Vocabulary Qualification for run: {run_id}")
    
    # Pre-compile regexes for fast matching (normalizing the vocab terms to match normalized text)
    phrase_patterns = [re.compile(r'\b' + re.escape(normalize_text(p)) + r'\b') for p in vocab.phrases]
    verb_patterns = [re.compile(r'\b' + re.escape(normalize_text(p)) + r'\b') for p in vocab.verbs]
    object_patterns = [re.compile(r'\b' + re.escape(normalize_text(p)) + r'\b') for p in vocab.objects]
    
    total_reviews = 0
    rejected = 0
    qualified = 0
    total_score = 0
    total_phrase_matches = 0
    total_verb_matches = 0
    total_object_matches = 0
    
    rejected_ids = []
    
    offset = 0
    limit = 1000
    while True:
        response = supabase.table("raw_reviews") \
            .select("id, raw_text") \
            .eq("run_id", run_id) \
            .eq("status", "pending") \
            .range(offset, offset + limit - 1) \
            .execute()
            
        rows = response.data
        if not rows:
            break
            
        for row in rows:
            total_reviews += 1
            text = normalize_text(row.get("raw_text", ""))
            
            phrase_matches = sum(1 for p in phrase_patterns if p.search(text))
            verb_matches = sum(1 for p in verb_patterns if p.search(text))
            object_matches = sum(1 for p in object_patterns if p.search(text))
            
            score = (phrase_matches * vocab.phrase_weight) + \
                    (verb_matches * vocab.verb_weight) + \
                    (object_matches * vocab.object_weight)
                    
            total_score += score
            total_phrase_matches += phrase_matches
            total_verb_matches += verb_matches
            total_object_matches += object_matches
            
            if score < 6:
                rejected += 1
                rejected_ids.append(row["id"])
            else:
                qualified += 1
                
        if len(rows) < limit:
            break
        offset += limit
        
    # Bulk update rejected IDs in batches
    if rejected_ids:
        print(f"  Updating {len(rejected_ids)} rejected reviews in database...")
        batch_size = 500
        for i in range(0, len(rejected_ids), batch_size):
            batch = rejected_ids[i:i + batch_size]
            supabase.table("raw_reviews").update({
                "status": "archived"
            }).in_("id", batch).execute()
            
    reduction = (rejected / total_reviews * 100) if total_reviews > 0 else 0
    avg_score = (total_score / total_reviews) if total_reviews > 0 else 0
    
    print("\n----------------------------------------")
    print("Behaviour Vocabulary Filtering Summary")
    print("----------------------------------------\n")
    print(f"Total Reviews: {total_reviews}")
    print(f"Rejected Before LLM: {rejected}")
    print(f"Qualified For LLM: {qualified}")
    print(f"Reduction: {reduction:.1f}%")
    print(f"Average Behaviour Score: {avg_score:.2f}")
    print(f"Phrase Matches: {total_phrase_matches}")
    print(f"Verb Matches: {total_verb_matches}")
    print(f"Object Matches: {total_object_matches}")
    print("\n----------------------------------------")
