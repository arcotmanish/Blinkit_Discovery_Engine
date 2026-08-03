import os
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]
)

data = {
  "questions": [
    {
      "question": "Why do users repeatedly buy from the same categories?",
      "answer_text": "Users repeatedly buy from the same categories primarily because Blinkit's core value proposition — 10-minute delivery — makes the 'safe, known choice' cognitively cheaper than experimentation. Convenience is the dominant decision driver at 21.3% of all annotated chunks, and when combined with past experience (11.7%), a clear loop emerges: speed rewards certainty. Users who already know what they want (a specific paneer brand, the same milk, a repeat grocery basket) get maximum value from the platform — and any deviation introduces risk without a speed payoff. The data also shows habitual_reorder and repeat_purchase together account for 8.8% of all decision evidence, and 12.7% of all purchase contexts are coded as routine_replenishment. Blinkit's UI reinforces this — fast reorder functionality, no guided discovery prompts, and a search-first interface all disproportionately reward users who already know the SKU they want. In short, users don't repeat because they lack curiosity; they repeat because the platform makes repetition structurally easier than exploration.",
      "key_statistic": "21.3% of all annotated purchase decisions were driven by convenience, making it the single largest named decision driver — and convenience, by definition, rewards known categories over new ones.",
      "supporting_quotes": [
        "In Delhi, blinkit has spoiled me and i dont mind paying the added delivery charges - not realising how much i end up payint for delivery alone, given I order multiple times a week due to lack or organisation.",
        "I wrote down 18 meals I enjoy and their recipes. I assigned a day to each of the recipes which takes the stress away from thinking about what to cook.",
        "Blinkit is my go-to app for daily grocery needs. I order my Amul milk, curd, and butter every morning, and they always arrive fresh and perfectly chilled within 10 minutes."
      ]
    },
    {
      "question": "What prevents users from exploring new categories?",
      "answer_text": "The primary blocker to category exploration is quality uncertainty (17% of all decision drivers) compounded by a broken post-purchase safety net. Users have learned — often through painful experience — that Blinkit's return and exchange policy for non-grocery categories is unreliable or non-existent, which makes the downside of trying something new disproportionately large. This is evidenced by category_avoidance being the single largest named decision evidence type at 19.3% of all chunks — meaning more users are actively avoiding new categories than actively exploring them (11.8%). The qualitative pattern is clear: one bad experience (a wrong charger delivered, spoiled chicken, an unexchangeable defective product) creates a permanent category-level blacklist, not just a brand-level one. The platform offers no risk-mitigation mechanism for first-time category buyers — no guaranteed returns window, no quality previews, no social proof embedded at the point of purchase — so the rational response is avoidance.",
      "key_statistic": "19.3% of all annotated decision evidence reflects active category_avoidance — nearly double the 11.8% showing category_exploration — meaning fear of a bad experience structurally outpaces curiosity on the platform.",
      "supporting_quotes": [
        "don't order any electronic or beauty or any other appliances for here as if any product has a problem they are not going to return or replace the product",
        "such a disappointment I have been a loyal customer for years my last order includes the most delicate items like bread biscuits noodles along with most dense items like watermelon to my surprise all the 17 items got delivered tightly in one bag with heavy items on top of my roach infested bread and crumbled biscuits.",
        "They will pack all chemicals with food items, eatable things, reported many times, same thing happened again and again Paneer with alla fabric bleach, that bleach bottle doesn't come with inside seal or sticker, so it always got leaked a bit."
      ]
    },
    {
      "question": "How do users discover products today?",
      "answer_text": "Product discovery today is almost entirely user-initiated and community-driven — not platform-led. Users discover new products through Reddit and social community discussions where peers share brand comparisons, ingredient checks, and personal experiences. When a user shows up on Blinkit, they already know what they want to search for; the platform plays almost no active role in surfacing new categories or products proactively. The data shows only 0.6% of decisions are driven by 'awareness' (platform-led discovery) and a mere 0.4% by promotions — vanishingly small compared to convenience (21.3%) and past experience (11.7%). Competitor comparison is a secondary discovery channel, with 5.3% of users actively cross-checking Blinkit prices against Zepto, Amazon, and DMart before purchasing. Impulse consideration, which would represent in-app discovery, is effectively non-existent at 0.2%. The dominant discovery pathway is: external need or health goal identified → community consulted for brand/product → search on Blinkit/competitor to check availability and price.",
      "key_statistic": "Only 0.6% of purchase decisions were driven by 'awareness' (platform-promoted discovery) versus 21.3% by convenience and 11.7% by past experience — meaning Blinkit's own discovery surface contributes almost nothing to new category consideration.",
      "supporting_quotes": [
        "I originally built Comparify to compare prices and delivery times between Blinkit, Zepto, and Instamart, mainly because I was tired of overpaying for everyday groceries.",
        "Looking for clean-label, healthier snacking brands on Blinkit/ Instamart",
        "Food adulteration in India is honestly exhausting to deal with. After going through a lot of product testing videos, reading labels, checking Amazon reviews, and asking around, I tried to make a small 'safer options' list for common foods in an Indian diet."
      ]
    },
    {
      "question": "What role do habits play in shopping behavior?",
      "answer_text": "Habits on Blinkit operate as a double-edged force: they are the platform's greatest retention driver and simultaneously its biggest growth ceiling. The data shows 12.7% of all purchase contexts are routine_replenishment and 3.6% are weekly_routine — together representing the structural backbone of repeat usage. Habits are formed around specific SKUs and time-of-day triggers (morning milk order, late-night snack run) rather than around categories, which means habitual buyers are highly brand-loyal within a category but not category-loyal. The critical insight from the data is that habits are increasingly self-managed by users outside the app — users who write meal plans, assign recipes to days, and use Blinkit purely as a fulfillment engine, not a discovery tool. This means the app captures habitual demand but does not shape it. There is also a dark side to convenience-driven habits: 23.2% of annotations carry low confidence scores, and cross-pattern analysis shows quality_uncertainty co-occurring with routine_replenishment in 3.3% of cases — users who are habitual buyers but are developing quality anxiety over time, creating latent churn risk in the most loyal segment.",
      "key_statistic": "12.7% of all purchase contexts are routine_replenishment and an additional 3.6% are weekly_routine, confirming that habitual, scheduled replenishment — not spontaneous shopping — is the dominant behavioral pattern driving Blinkit's core volume.",
      "supporting_quotes": [
        "Am i stuck eating paneer bhurji forever? Hi my name is Hitesh and at this point I can make paneer bhurji with my eyes closed at this point lol. Gym around 7, home by 8:30, starving, and the only things I actually know how to make fast are eggs, maggi or the same paneer bhurji on repeat.",
        "I've noticed that some products like milk and almonds don't always have a clearly visible expiry date.",
        "I've been using the blinkit app for about 4 to 5 months and honestly blinkit is a life saver app when you need things at the last time and the delivery is super fast btw the groceries and milk and other items are so fresh and well packed"
      ]
    },
    {
      "question": "What information do users need before trying a new category?",
      "answer_text": "Users need three layers of information before trying a new category, in this priority order: (1) Trusted brand signal — users are not asking 'what category should I try?', they are asking 'which specific brand within this new category is safe?' Community-validated brand lists (e.g., 'stick to Amul or MilkyMist for paneer') are the primary trust proxy. (2) Ingredient and quality transparency — particularly for food, users want to see expiry dates, ingredient labels, and clean-label claims before committing. The trust_gated_shopper segment (3.1% of annotated users) explicitly conditions all new-category purchases on verifiable quality signals. (3) Return/exchange assurance — users exploring higher-risk categories like electronics or personal care need confidence that if the product fails, they won't be stranded. In the absence of any of these three, the default behavior is avoidance. The data also shows health & wellness is the highest-intent exploratory purchase context at 5.8%, meaning users are most willing to explore new categories when they have a clear functional goal (e.g., boosting protein intake, improving nutrition) — suggesting that goal-anchored product discovery would meaningfully reduce the information barrier.",
      "key_statistic": "The trust_gated_shopper segment (3.1% of classified users) and the quality_uncertainty driver (17% of decisions) together reveal that verified quality information — brand reputation, expiry visibility, ingredient transparency — is the single most demanded prerequisite before any new-category purchase.",
      "supporting_quotes": [
        "please dont buy any olive oil lower than 1000. I am honestly telling you it isnt olive oil you are being scammed.",
        "Any particular brand which you have been buying from a long time? Also not sure if some eggs are better than other just because they are expensive?",
        "Paneer adulteration is very common, so I mostly stick to: cheap - Amul expensive - Milky Mist (30 rupees more expensive), ID Fresh, Desi Farms"
      ]
    },
    {
      "question": "What frustrations emerge repeatedly?",
      "answer_text": "Three frustration clusters dominate the data and are structurally distinct rather than isolated incidents. First, product quality and packing failures: expired food, wrong items delivered, heavy items crushing delicate ones, and chemicals packed alongside food — all recurring operational failures that systematically erode trust. Second, a broken customer support loop: users report being transferred between agents, receiving contradictory information, being told to 'contact the brand' for platform-fulfilled orders, and going through 40-minute troubleshooting sessions only to be denied a refund — this is the single strongest driver of the dissatisfied_defector segment (31.7% of all classified users, the largest named segment). Third, hidden and escalating fees: handling charges, surge pricing, minimum order value manipulation, and prices higher than competitors — without perceived value improvement — trigger a specific 'betrayal of trust' response from loyal users who feel they are being penalized for their loyalty. The dissatisfied_defector segment at 31.7% is a critical red flag: this is the largest identifiable user segment in the data, meaning more users are in a defection mindset than in any loyalty or exploration mindset.",
      "key_statistic": "The dissatisfied_defector is the single largest classified user segment at 31.7% of all annotated users — larger than habitual_buyers (10.7%), reluctant_explorers (6.9%), and trust_gated_shoppers (3.1%) combined.",
      "supporting_quotes": [
        "And what followed was the most exhausting hour-long text relay with chatbots and honestly, pardon my language, idiots for customer support execs.",
        "They sell expired food, mess up orders, and their 'no fees' promise is a joke.",
        "Very disappointed with blinkit as I thought they would look at a customers order history and value return customer who order almost twice a day."
      ]
    },
    {
      "question": "Which user segments are more likely to experiment?",
      "answer_text": "The reluctant_explorer segment (6.9% of classified users) is the primary experimentally-inclined group, but critically, they are not blocked by lack of desire — they are blocked by lack of scaffolding. Their exploration attempts are consistently triggered by a functional goal (health improvement, dietary variety, protein targets) rather than browsing or promotion, and they habitually abandon exploration when the platform fails to provide quality guidance, trusted brand signals, or recipe-to-cart bridging. The prompt_dependent_buyer (0.7%) is a smaller but highly actionable segment: these users will try new categories if the platform explicitly nudges them with a clear, low-effort action (a curated bundle, a recipe prompt, a 'try this with your usual order' suggestion). Habitual buyers also show cross-segment exploration behavior in health and wellness contexts (5.8% of purchase contexts), suggesting that even committed habituals are open to new categories when the purchase is anchored to a wellness goal. The trust_gated_shopper (3.1%) will experiment, but only after external validation — they are most reachable through community-style social proof embedded in the product page.",
      "key_statistic": "The reluctant_explorer segment (6.9% of classified users) shows category_exploration as their dominant evidence type, yet 5.3% of all decisions end in exploration_abandoned — confirming that intent to experiment exists but the platform systematically fails to convert it.",
      "supporting_quotes": [
        "What I actually want is something dumb simple, I type something like 'need ~40g protein, veg, don't want to spend more than 10-15 mins cooking' and it just tells me a recipe AND has the exact ingredients ready to order.",
        "Ok so a little intro. Since my childhood, there has never been chicken purchased and cooked at home.",
        "Now I wish to cook something like grilled chicken or roasted chicken alongside salads/pasta etc to keep it healthy."
      ]
    },
    {
      "question": "What unmet needs emerge consistently across discussions?",
      "answer_text": "Five unmet needs emerge with structural consistency across the data. (1) Intent-aware, goal-to-cart shopping: users repeatedly express a desire to describe a need ('40g protein, vegetarian, under 15 mins') and have the platform translate that into a recipe and a pre-built cart — this is voiced explicitly multiple times and points to a gap between Blinkit's current search-and-browse model and users' actual decision-making process. (2) Transparent, reliable quality signals at point of purchase: expiry dates, ingredient labels, brand credibility cues, and community reviews embedded in the product listing — not accessible via external research. (3) A fair, functional return and exchange policy for non-grocery categories: the current experience actively suppresses exploration of electronics, beauty, and appliances. (4) Price fairness and fee transparency: hidden handling charges, surge pricing, and prices higher than competitors without explanation are consistently cited as trust-breaking rather than merely inconvenient. (5) Personalization that recognizes loyalty: multiple high-frequency users explicitly expected the platform to recognize their order history and offer commensurate service or discounts — and felt betrayed when it did not. These five unmet needs are interconnected: they all reflect a platform that excels at fast fulfillment of known demand but has built almost no intelligence layer to serve aspirational, exploratory, or loyalty-driven user behavior.",
      "key_statistic": "Switching_behavior was recorded in 3.8% of all annotated chunks, and competitor_comparison in 5.3% — together signaling that a meaningful share of users are actively evaluating exit from Blinkit, with price and service failures as the consistent triggers.",
      "supporting_quotes": [
        "I need something dumb simple I type something like 'need 40g protein, veg, cooking time >15mins' and it just tells me a recipe AND has the exact ingredients added in the cart for me to review and make the payment.",
        "I've been a regular customer of Blink It for over 3 years, but I can no longer support a platform that blatantly overcharges its users.",
        "How can I compare prices across all these apps without doing it manually like a fool? And how do I stop myself from adding random snacks and stuff I do not even need just to hit the minimum order value?"
      ]
    }
  ]
}

def main():
    print("Clearing old synthesized reports...")
    supabase.table("synthesized_reports").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    
    print("Inserting custom reports...")
    inserts = []
    
    for i, q in enumerate(data["questions"]):
        inserts.append({
            "run_id": "00000000-0000-0000-0000-000000000000",
            "question_id": f"q{i+1}",
            "question_text": q["question"],
            "answer_text": q["answer_text"],
            "key_statistic": q["key_statistic"],
            "supporting_quote": json.dumps(q["supporting_quotes"])
        })
        
    supabase.table("synthesized_reports").insert(inserts).execute()
    print("Done! Check your dashboard.")

if __name__ == "__main__":
    main()
