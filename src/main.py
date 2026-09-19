import os
import time
import random
import feedparser
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from scraper import scrape_heavy_article
from filter_engine import is_relevant
from extractor import extract_entities
from database import filter_existing_urls, save_article
from sheets_sync import append_to_sheet

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1MlBvANu6ePWqQSWT9GlQbG0ZhrIm8_yvGTiE1_KeztE")
MAX_SCRAPES_PER_RUN = 50 

# The user's massively requested list of exact topic URLs
HTML_TOPICS = [
    "https://www.aajtak.in/topic/saharanpur", "https://www.aajtak.in/topic/shamli", "https://www.aajtak.in/topic/muzaffarnagar", 
    "https://www.aajtak.in/topic/bijnor", "https://www.aajtak.in/topic/moradabad", "https://www.aajtak.in/topic/sambhal",
    "https://www.aajtak.in/topic/lucknow", "https://www.aajtak.in/topic/varanasi", "https://www.aajtak.in/topic/gorakhpur",
    "https://www.uptak.in/neighbouring-news/agra", "https://www.uptak.in/neighbouring-news/ayodhya", "https://www.uptak.in/neighbouring-news/kanpur",
    "https://www.uptak.in/neighbouring-news/lucknow", "https://www.uptak.in/neighbouring-news/varanasi", "https://www.uptak.in/politics",
    "https://hindi.news18.com/news/uttar-pradesh/lucknow/", "https://hindi.news18.com/news/uttar-pradesh/varanasi/",
    "https://navbharattimes.indiatimes.com/metro/lucknow/articlelist/21248218.cms", "https://navbharattimes.indiatimes.com/state/uttar-pradesh/noida/articlelist/2313728.cms",
    "https://www.bhaskar.com/local/uttar-pradesh/lucknow", "https://www.bhaskar.com/local/uttar-pradesh/varanasi",
    "https://www.jagran.com/uttar-pradesh/lucknow-city", "https://www.jagran.com/uttar-pradesh/kanpur-city",
    "https://up.punjabkesari.in/lucknow", "https://up.punjabkesari.in/up-sp", "https://up.punjabkesari.in/up-bjp",
    "https://hindi.oneindia.com/news/lucknow/", "https://hindi.oneindia.com/news/varanasi/"
]

RSS_FEEDS = [
    "https://www.bhaskar.com/rss-feed/2322/",
    "https://cms.patrika.com/blog/location/lucknow-news/feed/",
    "https://hindi.news18.com/rss/uttar-pradesh.xml",
    "https://zeenews.india.com/hindi/india/up-uttarakhand/rss.xml",
    "https://www.livehindustan.com/rss/state/uttar-pradesh",
    "https://www.abplive.com/states/up-uk/feed",
    "https://ndtv.in/uttar-pradesh/rss",
    "https://english.jagran.com/rss/politics.xml",
    "https://rsshub.app/twitter/user/yadavakhilesh",
    "https://rsshub.app/twitter/user/myogiadityanath"
]

def fetch_direct_news_feeds():
    print("Fetching directly from Native News RSS Feeds & HTML Topic Pages...")
    article_data = {}
    time_limit = time.time() - (48 * 3600)
    
    # 1. RSS Fetching
    for feed_url in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:10]: 
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    if time.mktime(entry.published_parsed) < time_limit: continue 
                
                if hasattr(entry, 'link'):
                    clean_url = entry.link.split('?')[0]
                    article_data[clean_url] = {"title": entry.get("title", ""), "summary": entry.get("summary", "")}
        except Exception: pass
        
    # 2. HTML Topic Fetching (Lightweight Link Extraction)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    
    # Randomly pick 10 HTML topics per run so we don't timeout the GitHub action doing HTTP requests
    sampled_topics = random.sample(HTML_TOPICS, min(10, len(HTML_TOPICS)))
    for topic_url in sampled_topics:
        try:
            res = requests.get(topic_url, headers=headers, timeout=5)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    # Filter for likely article links (usually long, contain dates, or html/cms extensions)
                    if href.startswith("/") and len(href) > 30:
                        domain = urllib.parse.urlparse(topic_url).netloc
                        href = f"https://{domain}{href}"
                    
                    if "http" in href and len(href) > 40 and ("news" in href or ".html" in href or ".cms" in href):
                        clean_url = href.split('?')[0]
                        if clean_url not in article_data:
                            article_data[clean_url] = {"title": a_tag.get_text(strip=True)[:100], "summary": ""}
        except Exception: pass
            
    return article_data

def run_pipeline():
    print("Starting Direct Native Feed Pipeline...")
    
    live_articles = fetch_direct_news_feeds()
    print(f"Found {len(live_articles)} recent links directly from sources.")
    if not live_articles: return
    
    new_urls = filter_existing_urls(list(live_articles.keys()))
    print(f"Deduplication: {len(new_urls)} brand new links to evaluate.")
    if not new_urls: return

    scraped_count = 0

    for url in new_urls:
        if scraped_count >= MAX_SCRAPES_PER_RUN:
            break

        meta = live_articles[url]
        combined_meta_text = f"{url} {meta['title']} {meta['summary']}"
        if not is_relevant(combined_meta_text):
            continue 
            
        text = scrape_heavy_article(url)
        if not text or len(text) < 50:
            continue
            
        print("   -> Extracting Entities via Groq (with Fallback Roll-over)...")
        extracted_data = extract_entities(text)
        if not extracted_data:
            continue
            
        scraped_count += 1
            
        source = "unknown"
        if "twitter" in url or "rsshub" in url: source = "x_twitter"
        else:
            for s in ["bhaskar", "patrika", "news18", "zeenews", "livehindustan", "abplive", "ndtv", "jagran", "aajtak", "uptak", "navbharattimes", "punjabkesari", "oneindia"]:
                if s in url.lower(): source = s; break
            
        record = {
            "article_url": url,
            "source": source,
            "activity_type": str(extracted_data.get("activity_type", "other")),
            "electoral_relevance": str(extracted_data.get("electoral_relevance", "none")),
            "summary": extracted_data.get("summary", ""),
            "raw_json": extracted_data
        }
        
        save_article(record)
        
        now = datetime.now()
        row = [
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            url, 
            source, 
            record["activity_type"], 
            record["electoral_relevance"], 
            str(extracted_data.get("district", "")),
            str(extracted_data.get("constituency", "")),
            str(extracted_data.get("local_geography", "")),
            ", ".join(extracted_data.get("parties_involved", [])),
            ", ".join(extracted_data.get("key_leaders", [])),
            ", ".join(extracted_data.get("keywords", [])),
            record["summary"],
            text[:10000]
        ]
        append_to_sheet(SPREADSHEET_ID, row)
        
    print(f"\nPipeline complete. Processed {scraped_count} native articles.")

if __name__ == "__main__":
    run_pipeline()
