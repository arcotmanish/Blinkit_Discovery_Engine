"""
Google Play Corpus Analysis Script
Analyses the ~4,600 collected reviews from the last production run.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.client import supabase

# ---- 1. Find the last production run ----
try:
    with open("last_production_run.txt") as f:
        run_id = f.read().strip()
    print(f"Analysing run: {run_id}")
except FileNotFoundError:
    # Fallback: get the most recent completed run
    res = supabase.table("pipeline_runs").select("id,mode,status,started_at").order("started_at", desc=True).limit(5).execute()
    print("Recent runs:")
    for r in res.data:
        print(f"  {r['id']} | {r['mode']} | {r['status']} | {r.get('started_at','?')}")
    run_id = res.data[0]['id']
    print(f"\nUsing most recent: {run_id}")

print()

# ---- 2. Total review counts by source ----
res_all = supabase.table("raw_reviews").select("id,source,word_count,signal_score,language,status,raw_text,rating").eq("run_id", run_id).execute()
reviews = res_all.data
print(f"Total reviews fetched: {len(reviews)}")

sources = {}
for r in reviews:
    src = r.get("source", "unknown")
    sources.setdefault(src, []).append(r)

print("\nBy source:")
for src, items in sources.items():
    print(f"  {src}: {len(items)}")

print()

# ---- 3. Google Play detailed analysis ----
gp = sources.get("play_store", [])
print(f"=== Google Play Analysis ({len(gp)} reviews) ===")

if gp:
    import statistics

    # Word counts
    word_counts = [r.get("word_count") or len(r.get("raw_text","").split()) for r in gp]
    valid_wc = [w for w in word_counts if w > 0]
    print(f"\nWord Count Stats:")
    print(f"  Mean:   {statistics.mean(valid_wc):.1f}")
    print(f"  Median: {statistics.median(valid_wc):.1f}")
    print(f"  StdDev: {statistics.stdev(valid_wc):.1f}")
    print(f"  Min:    {min(valid_wc)}")
    print(f"  Max:    {max(valid_wc)}")

    # Substantive reviews (>= 20 words)
    substantive = [w for w in valid_wc if w >= 20]
    minimal = [w for w in valid_wc if 10 <= w < 20]
    trivial = [w for w in valid_wc if w < 10]
    print(f"\nReview Length Buckets:")
    print(f"  Substantive (≥20 words): {len(substantive)} ({100*len(substantive)/len(valid_wc):.1f}%)")
    print(f"  Minimal (10-19 words):   {len(minimal)} ({100*len(minimal)/len(valid_wc):.1f}%)")
    print(f"  Trivial (<10 words):     {len(trivial)} ({100*len(trivial)/len(valid_wc):.1f}%)")

    # Signal scores
    scores = [r.get("signal_score") for r in gp if r.get("signal_score") is not None]
    if scores:
        print(f"\nSignal Score Stats (n={len(scores)}):")
        print(f"  Mean:   {statistics.mean(scores):.3f}")
        print(f"  Median: {statistics.median(scores):.3f}")
        above_06 = [s for s in scores if s >= 0.6]
        above_07 = [s for s in scores if s >= 0.7]
        above_08 = [s for s in scores if s >= 0.8]
        print(f"  ≥0.6 (high-signal):  {len(above_06)} ({100*len(above_06)/len(scores):.1f}%)")
        print(f"  ≥0.7 (very high):    {len(above_07)} ({100*len(above_07)/len(scores):.1f}%)")
        print(f"  ≥0.8 (elite):        {len(above_08)} ({100*len(above_08)/len(scores):.1f}%)")

    # Rating distribution
    ratings = [r.get("rating") for r in gp if r.get("rating") is not None]
    if ratings:
        from collections import Counter
        dist = Counter(ratings)
        print(f"\nRating Distribution (n={len(ratings)}):")
        for star in sorted(dist.keys()):
            bar = "█" * int(dist[star] * 30 / max(dist.values()))
            print(f"  {star}★: {dist[star]:4d} ({100*dist[star]/len(ratings):.1f}%) {bar}")
        avg_rating = sum(ratings) / len(ratings)
        print(f"  Average rating: {avg_rating:.2f}")

    # Status distribution
    statuses = {}
    for r in gp:
        s = r.get("status","unknown")
        statuses[s] = statuses.get(s, 0) + 1
    print(f"\nStatus Distribution:")
    for s, c in sorted(statuses.items(), key=lambda x: -x[1]):
        print(f"  {s}: {c}")

    # Language
    langs = {}
    for r in gp:
        l = r.get("language", "unknown")
        langs[l] = langs.get(l, 0) + 1
    print(f"\nLanguage Distribution:")
    for l, c in sorted(langs.items(), key=lambda x: -x[1]):
        print(f"  {l}: {c}")

    # Sample extracted reviews (high signal)
    print(f"\n--- Sample High-Signal Reviews (signal_score >= 0.75) ---")
    high_signal = [r for r in gp if (r.get("signal_score") or 0) >= 0.75]
    for rev in high_signal[:3]:
        text = rev.get("raw_text","")[:200]
        print(f"  [{rev.get('rating')}★ | score={rev.get('signal_score'):.2f} | wc={rev.get('word_count')}]")
        print(f"  {text}")
        print()

print()
# ---- 4. Reddit analysis (if any data) ----
rd = sources.get("reddit", [])
print(f"=== Reddit Analysis ({len(rd)} posts) ===")
if rd:
    word_counts_r = [r.get("word_count") or len(r.get("raw_text","").split()) for r in rd]
    valid_wc_r = [w for w in word_counts_r if w > 0]
    if valid_wc_r:
        import statistics
        print(f"  Mean word count: {statistics.mean(valid_wc_r):.1f}")
        substantive_r = [w for w in valid_wc_r if w >= 20]
        print(f"  Substantive (≥20 words): {len(substantive_r)} ({100*len(substantive_r)/len(valid_wc_r):.1f}%)")
else:
    print("  No Reddit data found in this run.")
