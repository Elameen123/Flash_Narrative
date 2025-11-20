import nltk
from nltk.probability import FreqDist
from collections import Counter
import re
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser
from nltk.collocations import BigramAssocMeasures, BigramCollocationFinder
import pandas as pd

# --- NLTK Setup ---
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("NLTK data not found. Downloading...")
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)

stop_words = set(nltk.corpus.stopwords.words('english'))
stop_words.update(['com', 'www', 'http', 'https', 'co', 'uk', 'amp', 'rt', 'via', 'status', 'twitter'])

# --- 1. KEYWORD SENTIMENT ANALYSIS (RICH VERSION) ---
def analyze_sentiment_keywords(text):
    """
    Analyzes sentiment based on extensive keywords.
    Returns a single sentiment string.
    """
    if not text: return 'neutral'
    text_lower = str(text).lower()

    # --- EXTENSIVE KEYWORD LISTS (From Uploaded File) ---
    positive_kws = [
        'good', 'great', 'excellent', 'positive', 'love', 'awesome', 'best', 'happy', 'like', 'amazing', 'superb',
        'fantastic', 'recommend', 'perfect', 'thrilled', 'delighted', 'satisfied', 'easy', 'seamless',
        'wins', 'won', 'award', 'recognition', 'honoured', 'named as', 'ranked #1', 'leading', 'top-tier',
        'successful', 'successfully', 'oversubscribed', 'exceeds expectations', 'confidence',
        'grows', 'growth', 'rise', 'increase', 'expansion', 'accelerate', 'boost', 'outperforms',
        'launches', 'unveils', 'introduces', 'new initiative', 'new product', 'new feature',
        'profit', 'profits', 'profitable', 'strong performance', 'robust', 'stronger',
        'upgrades', 'stable outlook', 'reaffirms', 'commitment', 'strengthening'
    ]
    appreciation_kws = [
        'thank', 'thanks', 'grateful', 'kudos', 'congratulations', 'congrats', 'props', 'helpful',
        'appreciate', 'appreciation', 'lauds', 'commends', 'praised', 'legacy', 'honoring',
        'empower', 'support', 'champions', 'donates', 'donation', 'csr', 'esg', 'community', 'foundation', 'sponsors'
    ]
    negative_kws = [
        'bad', 'poor', 'terrible', 'negative', 'hate', 'awful', 'worst', 'sad', 'dislike', 'broken',
        'disappointed', 'frustrated', 'horrible', 'useless', 'embarrassing',
        'fail', 'failed', 'issue', 'problem', 'avoid', 'scam', 'fraud', 'fraudulent', 'allegation', 'alleges',
        'downtime', 'glitch', 'glitches', 'crashes', 'down', 'outage', 'unauthorized',
        'fined', 'sanctioned', 'penalty', 'lawsuit', 'court', 'arrest', 'efcc',
        'crisis', 'vulnerabilities', 'threats', 'risk', 'stifling', 'rift',
        'loss', 'losses', 'decline', 'dip', 'drop', 'slump', 'erosion', 'undersubscribed',
        'complaint', 'complaints', 'fume', 'laments', 'outcry', 'slams'
    ]
    anger_kws = [
        'angry', 'furious', 'rage', 'mad', 'outrage', 'pissed', 'fuming', 'livid', 'worst!',
        'stealing', 'thieves', 'scammed', 'disgusted'
    ]
    mixed_kws = [
        'but', 'however', 'although', 'yet', 'still', 'despite', 'while', 'though'
    ]

    pos_count = sum(1 for k in positive_kws if re.search(r'\b' + re.escape(k) + r'\b', text_lower))
    neg_count = sum(1 for k in negative_kws if re.search(r'\b' + re.escape(k) + r'\b', text_lower))
    anger_count = sum(1 for k in anger_kws if re.search(r'\b' + re.escape(k) + r'\b', text_lower))
    app_count = sum(1 for k in appreciation_kws if re.search(r'\b' + re.escape(k) + r'\b', text_lower))
    has_mixed = any(re.search(r'\b' + re.escape(k) + r'\b', text_lower) for k in mixed_kws)

    if anger_count > 0: return 'anger'
    if (pos_count > 0 and neg_count > 0) or (has_mixed and (pos_count > 0 or neg_count > 0)): return 'mixed'
    if neg_count > 0: return 'negative'
    if pos_count > 0: return 'positive'
    if app_count > 0: return 'appreciation'
    return 'neutral'

# --- 2. KEYWORD EXTRACTION (SMART) ---
def extract_keywords(all_text, brand, competitors=None):
    """
    Extracts top single keywords and bigrams.
    Includes logic to filter out the Brand Name itself from the results.
    """
    if not competitors: competitors = []
    
    tokens = nltk.word_tokenize(all_text.lower())
    
    dynamic_stop_words = stop_words.copy()
    if brand: dynamic_stop_words.add(brand.lower())
    for c in competitors:
        dynamic_stop_words.add(c.lower())
    
    # Generic business/bank words to filter
    dynamic_stop_words.update(['bank', 'plc', 'ltd', 'group', 'holdings', 'customer', 'customers', 'today', 'year'])

    filtered_tokens = [t for t in tokens if len(t) > 2 and t.isalpha() and t not in dynamic_stop_words]
    
    unigram_freq = FreqDist(filtered_tokens)
    finder = BigramCollocationFinder.from_words(filtered_tokens)
    
    # Only consider bigrams that appear at least twice
    finder.apply_freq_filter(2) 
    bigram_freq = finder.ngram_fd

    combined_freq = Counter()
    for word, freq in unigram_freq.items():
        combined_freq[word] += freq
    for phrase_tuple, freq in bigram_freq.items():
        combined_freq[" ".join(phrase_tuple)] += freq

    return combined_freq.most_common(10)

# --- 3. HELPER: TIME FILTER ---
def filter_by_hours(full_data, hours):
    """ Filters data points older than 'hours'. """
    if not hours: return full_data
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    filtered = []
    
    for item in full_data:
        try:
            # Handle various date formats or existing datetime objects
            raw_date = item.get('date')
            if isinstance(raw_date, datetime):
                item_time = raw_date
            else:
                item_time = dateparser.parse(str(raw_date))
            
            if item_time.tzinfo is None:
                item_time = item_time.replace(tzinfo=timezone.utc)
                
            if item_time >= cutoff:
                filtered.append(item)
        except Exception:
            # If date parsing fails, keep it to be safe (or drop it depending on preference)
            filtered.append(item)
    return filtered

# --- 4. MAIN KPI ENGINE (HARMONIZED) ---
def compute_kpis(full_data, campaign_messages, brand, competitors=None, industry=None, hours=None):
    """
    Calculates KPIs.
    - Works with 'hours' filter (Live mode).
    - Works with optional 'competitors' list (Demo mode compatibility).
    - Respects existing sentiment (from LLM) but backfills if missing.
    """
    if not competitors: competitors = []
    
    # 1. Apply Time Filter
    if hours:
        full_data = filter_by_hours(full_data, hours)

    if not full_data:
        return {'sentiment_ratio': {}, 'sov': [], 'mis': 0, 'mpi': 0, 'engagement_rate': 0, 'reach': 0, 'all_brands': [brand]}

    total_mentions = len(full_data)
    all_brands_list = [brand] + competitors
    
    tones = []
    themes = []
    brand_counts = Counter()
    
    # --- Analysis Loop ---
    for item in full_data:
        text = item.get('text', '')
        text_lower = str(text).lower()

        # A. Sentiment: Use existing (from LLM) or calculate (Fallback)
        if not item.get('sentiment'):
            item['sentiment'] = analyze_sentiment_keywords(text)
        tones.append(item['sentiment'])
        
        # B. Theme: Use existing or calculate (Rich Logic)
        if not item.get('theme'):
            if any(kw in text_lower for kw in ['csr', 'esg', 'donation', 'community', 'foundation', 'initiative', 'sustainability', 'empower', 'scholarship']):
                item['theme'] = 'CSR/ESG'
            elif any(kw in text_lower for kw in ['ceo', 'gmd', 'profit', 'results', 'acquisition', 'corporate', 'raise', 'capital', 'bond', 'earnings', 'dividend', 'financials', 'shareholders']):
                item['theme'] = 'Corporate'
            elif any(kw in text_lower for kw in ['partner', 'sponsorship', 'marathon', 'zecathon', 'collaboration', 'champions']):
                item['theme'] = 'Partnership/Sponsorship'
            elif any(kw in text_lower for kw in ['app', 'loan', 'card', 'customer service', 'downtime', 'glitch', 'e-channel', 'transfer', 'pos', 'digital', 'feature', 'platform']):
                item['theme'] = 'Product/Service'
            elif any(kw in text_lower for kw in ['fraud', 'cbn', 'efcc', 'fine', 'court', 'scam', 'allegation', 'rift', 'lawsuit', 'crisis', 'vulnerability', 'sanction', 'erosion']):
                item['theme'] = 'Legal/Risk'
            else:
                item['theme'] = 'General News'
        themes.append(item['theme'])

        # C. Brand Detection (for SOV)
        # If 'mentioned_brands' isn't pre-calculated, do it now
        if 'mentioned_brands' not in item:
            found_brands = []
            # Check for known competitors + main brand
            for b_name in all_brands_list:
                if re.search(r'\b' + re.escape(b_name.lower()) + r'\b', text_lower):
                    found_brands.append(b_name)
            item['mentioned_brands'] = found_brands
        
        # Count for SOV
        mentions = item.get('mentioned_brands', [])
        if isinstance(mentions, str): mentions = [mentions]
        for b in mentions:
            brand_counts[b] += 1
            
    # --- SOV Calculation ---
    # Ensure we include brands that were passed in arguments + any found in data
    final_brand_list = set(all_brands_list)
    final_brand_list.update(brand_counts.keys())
    # Sort: Brand first, then others
    final_brand_list = sorted(list(final_brand_list), key=lambda x: (x.lower() != brand.lower(), x))
    
    total_appearances = sum(brand_counts.values())
    sov = [(brand_counts[b] / total_appearances * 100) if total_appearances > 0 else 0 for b in final_brand_list]

    # --- Ratios ---
    sentiment_counts = Counter(tones)
    sentiment_ratio = {tone: count / total_mentions * 100 for tone, count in sentiment_counts.items()}

    theme_counts = Counter(themes)
    theme_ratio = {theme: count / total_mentions * 100 for theme, count in theme_counts.items()}

    # --- MIS (Media Impact Score) ---
    # Sum 'authority' (default 5 if missing) for positive mentions
    mis = sum(item.get('authority', 5) for item in full_data if item.get('sentiment') in ['positive', 'appreciation'])
    
    # --- MPI (Message Penetration Index) ---
    matches = 0
    if campaign_messages:
        lower_campaign_messages = [msg.lower() for msg in campaign_messages]
        for item in full_data:
            if any(msg in item.get('text', '').lower() for msg in lower_campaign_messages):
                matches += 1
        mpi = (matches / total_mentions) * 100 if total_mentions > 0 else 0
    else: mpi = 0

    # --- Engagement Rate ---
    social_sources = ['reddit', 'fb', 'facebook', 'ig', 'instagram', 'threads', 'twitter', 'x', 'linkedin']
    total_engagement = 0
    num_social_mentions = 0
    
    for item in full_data:
        src = item.get('source', '').lower()
        if any(s in src for s in social_sources):
            try:
                likes = int(item.get('likes', 0) or 0)
                comments = int(item.get('comments', 0) or 0)
                total_engagement += (likes + comments)
                num_social_mentions += 1
            except (ValueError, TypeError): continue
                
    engagement_rate = total_engagement / num_social_mentions if num_social_mentions > 0 else 0
    
    # --- Total Reach ---
    reach = 0
    for item in full_data:
        try:
            r = item.get('reach', 0)
            reach += int(r if pd.notna(r) else 0)
        except: continue

    return {
        'sentiment_ratio': sentiment_ratio,
        'theme_ratio': theme_ratio,
        'sov': sov,
        'mis': mis,
        'mpi': mpi,
        'engagement_rate': engagement_rate,
        'reach': reach,
        'all_brands': final_brand_list,
        'analyzed_data': full_data
    }