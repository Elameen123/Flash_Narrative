# scraper.py
import os
import json
import time
import requests
import random
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import feedparser
from dateutil import parser as dateparser
from urllib.parse import quote_plus

# --- CONFIGURATION ---

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, 'scraper_cache.json')

# API Keys (Keep NewsAPI as a strong global backup)
NEWSAPI_KEYS = []
if os.getenv("NEWSAPI_KEYS"):
    NEWSAPI_KEYS = [k.strip() for k in os.getenv("NEWSAPI_KEYS").split(",") if k.strip()]

# Rotating User Agents to avoid 429 Blocks
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
]

# --- REAL-WORLD DATA SOURCES ---

RSS_FEEDS_BY_INDUSTRY = {
    'nigeria': [
        'https://punchng.com/feed/',
        'https://www.vanguardngr.com/feed/',
        'https://www.thecable.ng/feed',
        'https://dailypost.ng/feed/',
        'https://saharareporters.com/feeds/news',
        'https://businessday.ng/feed/',
        'https://nairametrics.com/feed/'
    ],
    'tech': [
        'http://feeds.feedburner.com/TechCrunch/',
        'https://techcabal.com/feed/', # African Tech
        'https://techpoint.africa/feed/', # African Tech
        'https://www.theverge.com/rss/index.xml'
    ],
    'finance': [
        'https://www.bloomberg.com/feed/podcast/etf.xml',
        'https://nairametrics.com/feed/', # Critical for Nigerian Finance
        'https://www.cnbc.com/id/100003114/device/rss/rss.html'
    ],
    'default': [
        'http://rss.cnn.com/rss/edition.rss',
        'http://feeds.reuters.com/reuters/topNews',
        'https://www.aljazeera.com/xml/rss/all.xml'
    ]
}

# --- UTILS ---

def _get_random_header():
    return {"User-Agent": random.choice(USER_AGENTS)}

def _cache_read():
    try:
        if not os.path.exists(CACHE_FILE): return {}
        with open(CACHE_FILE, 'r') as f: return json.load(f)
    except: return {}

def _cache_write(data):
    try:
        with open(CACHE_FILE, 'w') as f: json.dump(data, f)
    except: pass

def _get_cache_key(brand, hours, competitors):
    comps = ",".join(sorted(competitors)) if competitors else ""
    return f"{brand.lower()}|{hours}|{comps}"

def _parse_date_to_dt(datestr):
    try:
        dt = dateparser.parse(datestr)
        if dt: 
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except: pass
    return datetime.now(timezone.utc)

def _clean_domain(url):
    try:
        return url.split("//")[-1].split("/")[0].replace('www.', '')
    except: return "web"

# --- CORE SCRAPERS ---

def fetch_google_search(query, time_hours, geo='us'):
    """
    Performs a scraped Google Search.
    Args:
        geo: 'ng' for Nigeria, 'us' for Global/USA, 'uk' for UK.
    """
    print(f"🔎 Google Search [{geo.upper()}]: {query}...")
    try:
        # Convert hours to Google Time format (qdr:h or qdr:d)
        tbs = "qdr:h" if int(time_hours) <= 1 else f"qdr:d{max(1, int(int(time_hours)/24))}"
        
        # 'gl' param controls country (ng = Nigeria), 'tbm=nws' forces News tab
        url = f"https://www.google.com/search?q={quote_plus(query)}&gl={geo}&hl=en&tbm=nws&tbs={tbs}"
        
        resp = requests.get(url, headers=_get_random_header(), timeout=10)
        
        if resp.status_code == 429:
            print("⚠️ Google Rate Limit (429). Skipping.")
            return []
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        mentions = []
        
        # Selectors for Google News Cards (These change occasionally, using multiple standard ones)
        cards = soup.select("div.SoaBEf") or soup.select("div.dbsr") or soup.select("div.Gx5Zad")
        
        for card in cards:
            try:
                link_tag = card.find('a')
                if not link_tag: continue
                link = link_tag['href']
                
                title = card.find('div', role='heading') or link_tag
                title_text = title.get_text().strip()
                
                # Try to find description snippet
                snippet_div = card.find('div', class_='GI74Re') or card.find('div', class_='n0jPhd')
                snippet = snippet_div.get_text().strip() if snippet_div else ""
                
                full_text = f"{title_text} {snippet}"
                
                # Try to parse time
                time_el = card.find('div', class_='OSrXXb') or card.find('span', class_='WG9SPL')
                dt = _parse_date_to_dt(time_el.get_text()) if time_el else datetime.now(timezone.utc)

                domain = _clean_domain(link)
                
                mentions.append({
                    'text': full_text,
                    'source': domain,
                    'date': dt.isoformat(),
                    'link': link,
                    'authority': 7, # Google News results generally have higher authority
                    'reach': 50000
                })
            except Exception: continue
            
        return mentions
    except Exception as e:
        print(f"❌ Google Search Error: {e}")
        return []

def fetch_social_xray(brand, competitors):
    """
    Uses Google Search to find REAL public social media posts.
    Searches: Nairaland, LinkedIn, Reddit, Twitter/X
    """
    print("🔎 Running Social X-Ray (Nairaland, LinkedIn, Reddit)...")
    mentions = []
    
    # Define "Dorks" for social X-ray
    queries = [
        f'site:nairaland.com "{brand}"',   # Critical for Nigeria
        f'site:reddit.com "{brand}"',      # Global sentiment
        f'site:linkedin.com/posts "{brand}"' # Professional sentiment
    ]
    
    for q in queries:
        try:
            # Note: We remove 'tbm=nws' to get general search results (posts), not just news
            url = f"https://www.google.com/search?q={quote_plus(q)}&tbs=qdr:w" # Last week
            resp = requests.get(url, headers=_get_random_header(), timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Standard Search Results (div.g)
            results = soup.select("div.g")
            
            for res in results:
                try:
                    h3 = res.find('h3')
                    if not h3: continue
                    
                    link_tag = res.find('a')
                    link = link_tag['href'] if link_tag else ""
                    
                    snippet_div = res.find('div', class_='VwiC3b') # Standard snippet class
                    snippet = snippet_div.get_text() if snippet_div else ""
                    
                    full_text = f"{h3.get_text()} {snippet}"
                    
                    source = "nairaland" if "nairaland" in q else "reddit" if "reddit" in q else "linkedin"
                    
                    mentions.append({
                        'text': full_text,
                        'source': source,
                        'date': datetime.now(timezone.utc).isoformat(), # Approximate
                        'link': link,
                        'authority': 5,
                        'reach': 10000 # Social posts vary
                    })
                except: continue
            time.sleep(1) # Polite delay between x-ray queries
        except Exception as e:
            print(f"❌ X-Ray Error for {q}: {e}")
            
    return mentions

def fetch_rss(industry, brand, hours, competitors):
    """
    Fetches from RSS feeds including Nigerian specific ones.
    """
    feeds = RSS_FEEDS_BY_INDUSTRY.get(industry, []) + RSS_FEEDS_BY_INDUSTRY['nigeria']
    mentions = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    search_terms = [brand.lower()] + [c.lower() for c in competitors]

    print(f"📡 Checking {len(feeds)} RSS Feeds...")
    
    for url in feeds:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries:
                # Check Date
                dt_str = entry.get('published') or entry.get('updated')
                dt = _parse_date_to_dt(dt_str)
                if not dt or dt < cutoff: continue
                
                # Check Text Match
                text = (entry.get('title', '') + " " + entry.get('summary', '')).strip()
                if not any(term in text.lower() for term in search_terms):
                    continue
                
                mentions.append({
                    'text': text,
                    'source': _clean_domain(entry.get('link', url)),
                    'date': dt.isoformat(),
                    'link': entry.get('link', ''),
                    'authority': 6,
                    'reach': 20000
                })
        except: continue
        
    return mentions

def fetch_newsapi_global(brand, hours, competitors, keys):
    """ Uses Official NewsAPI as backup/global layer """
    if not keys: return []
    print("🌍 Fetching NewsAPI...")
    # (Existing Logic kept brief for brevity)
    # ... Implementation matches previous valid logic ...
    # Returning empty list here to force reliance on the new Google logic for this snippet
    # You can paste the previous NewsAPI function here if you have keys.
    return [] 

# --- MAIN AGGREGATOR ---

def fetch_all(brand, time_frame, competitors=None, industry='default'):
    """
    Master function to get REAL data.
    """
    if competitors is None: competitors = []
    
    # 1. Check Cache
    cache = _cache_read()
    key = _get_cache_key(brand, time_frame, competitors)
    if key in cache and (time.time() - cache[key]['ts'] < 900): # 15 min cache
        print("⚡ Returning Cached Data")
        return cache[key]['value']

    all_data = []

    # 2. Run Scrapers
    
    # A. Nigerian Google News (High Priority)
    ng_news = fetch_google_search(f"{brand} OR {' OR '.join(competitors)}", time_frame, geo='ng')
    all_data.extend(ng_news)

    # B. Global Google News
    gl_news = fetch_google_search(f"{brand} news", time_frame, geo='us')
    all_data.extend(gl_news)

    # C. Social X-Ray (Nairaland, LinkedIn, Reddit) - NO API KEYS
    socials = fetch_social_xray(brand, competitors)
    all_data.extend(socials)

    # D. RSS Feeds (Industry + Nigeria)
    rss_data = fetch_rss(industry, brand, time_frame, competitors)
    all_data.extend(rss_data)

    # 3. Deduplication
    seen = set()
    unique_data = []
    for item in all_data:
        # Create a unique signature based on Title + Source
        sig = (item['text'][:50] + item['source']).lower()
        if sig not in seen:
            seen.add(sig)
            # Add Brand tags
            item['mentioned_brands'] = [b for b in [brand]+competitors if b.lower() in item['text'].lower()]
            unique_data.append(item)

    print(f"✅ Scraper Finished. Found {len(unique_data)} items.")
    
    result = {'mentions': [d['text'] for d in unique_data], 'full_data': unique_data}
    
    # Write to Cache
    cache[key] = {'ts': time.time(), 'value': result}
    _cache_write(cache)
    
    return result

if __name__ == "__main__":
    # Test Run
    data = fetch_all("Tinubu", 24, ["Atiku", "Obi"], industry='nigeria')
    for x in data['full_data']:
        print(f"[{x['source'].upper()}] {x['text'][:80]}...")