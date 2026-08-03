from pipeline.stages.vocab_qualify import vocab, normalize_text
import re

text = "06 june 2026 blinkit no more reliable. got fed up from their service, they don't value your time . Nowadays they don't care about your health. They will pack all chemicals with food items,eatable things,reported many times ,same thing happened again and again Paneer with alla fabric bleach, that bleach bottle doesn't come with inside seal or sticker, so it always got leaked a bit. Can't post photo here otherwise can display the items . No words left ...:("

text_norm = normalize_text(text)

phrase_patterns = [(p, re.compile(r'\b' + re.escape(normalize_text(p)) + r'\b')) for p in vocab.phrases]
verb_patterns = [(p, re.compile(r'\b' + re.escape(normalize_text(p)) + r'\b')) for p in vocab.verbs]
object_patterns = [(p, re.compile(r'\b' + re.escape(normalize_text(p)) + r'\b')) for p in vocab.objects]

p_matches = [p[0] for p in phrase_patterns if p[1].search(text_norm)]
v_matches = [p[0] for p in verb_patterns if p[1].search(text_norm)]
o_matches = [p[0] for p in object_patterns if p[1].search(text_norm)]

score = (len(p_matches) * vocab.phrase_weight) + (len(v_matches) * vocab.verb_weight) + (len(o_matches) * vocab.object_weight)

print(f"Score: {score}")
print(f"Phrases: {p_matches}")
print(f"Verbs: {v_matches}")
print(f"Objects: {o_matches}")
