import os
import sys
import json

# Adjust path so db.client can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.client import supabase

run_id = '4a58551b-b5fd-469e-803f-b8871cab3a42'

# Replacements to make
replacements = {
    # q3: Clean-label snacking
    "Looking for clean-label, healthier snacking brands on Blinkit/ Instamart": "Looking for clean-label, healthier snacking brands on Blinkit. I’m specifically looking for recommendations for Khakhra and healthy snacks where brands bake their products, use no palm oil, and offer tried and tested options.",
    
    # q4: Expiry dates
    "I've noticed that some products like milk and almonds don't always have a clearly visible expiry date.": "I've noticed that some products like milk and almonds don't always have a clearly visible expiry date. Please ensure that expiry dates are clearly visible and perishable items are checked properly before delivery.",
    
    # q7: Chicken
    "Ok so a little intro. Since my childhood, there has never been chicken purchased and cooked at home.": "Since my childhood, there has never been chicken purchased and cooked at home. I wish to cook healthy grilled chicken frequently, and checked Blinkit and Zepto for trusted brands like Nutri chicken and Zorabian.",
    
    # q6: JioMart
    "They sell expired food, mess up orders, and their 'no fees' promise is a joke.": "JioMart sells expired food, messes up orders, and their 'no fees' promise is a joke. I finally switched to Blinkit; they charge a small fee, but I get fresh groceries and reliable deliveries."
}

# Fetch the existing reports
res = supabase.table('synthesized_reports').select('id, question_id, supporting_quote').eq('run_id', run_id).execute()

for row in res.data:
    try:
        quotes = json.loads(row['supporting_quote'])
        updated = False
        for i, quote in enumerate(quotes):
            for old_text, new_text in replacements.items():
                if old_text in quote:
                    quotes[i] = quote.replace(old_text, new_text)
                    updated = True
        
        if updated:
            supabase.table('synthesized_reports').update({
                'supporting_quote': json.dumps(quotes)
            }).eq('id', row['id']).execute()
            print(f"Updated q{row['question_id']}")
            
    except Exception as e:
        print(f"Error on {row['question_id']}: {e}")

print("Update complete!")
