# investor_match_mvp.py
# MVP with real-time article scraping, structured investor info, user-defined URL input, and historical timestamping

import requests
from bs4 import BeautifulSoup
import re
import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# -------------------- MODULE 1: SCRAPER WITH URL INPUT --------------------

def fetch_articles_from_user_input():
    st.sidebar.markdown("### Enter article URLs (one per line):")
    url_input = st.sidebar.text_area("Paste URLs", height=150)
    urls = [url.strip() for url in url_input.splitlines() if url.strip()]

    articles = []
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            paragraphs = soup.find_all('p')
            text = ' '.join([p.get_text() for p in paragraphs])
            articles.append({"url": url, "text": text})
        except Exception as e:
            st.warning(f"Failed to fetch {url}: {e}")
    return articles

# -------------------- MODULE 2: NLP EXTRACTOR --------------------

def extract_data_from_text(text, url):
    fund_pattern = r"([A-Z][a-zA-Z]+\s(?:Capital|Ventures|Partners|Group|Investments|Fund|Advisors))"
    ticket_keywords = r"(?i)(cheque|check|ticket|initial investment|typical investment|writes).*?(\$[\d,.]+(?:\s?[-to–]\s?\$?[\d,.]+)?(?:\s?(million|M|billion|B))?)"
    fund_size_pattern = r"\$[\d,.]+(?:\s?(million|billion|M|B))(?=.*?fund)"
    stage_keywords = ["seed", "early-stage", "growth-stage", "late-stage", "Series A", "Series B"]
    sector_keywords = ["consumer tech", "fintech", "edtech", "healthtech", "sustainability", "AI", "crypto"]
    geography_keywords = ["India", "Southeast Asia", "Singapore", "Indonesia", "Asia"]

    funds = list(set(re.findall(fund_pattern, text)))
    fund_size = re.findall(fund_size_pattern, text)
    ticket_info = re.findall(ticket_keywords, text)
    stages = [s for s in stage_keywords if s.lower() in text.lower()]
    sectors = [s for s in sector_keywords if s.lower() in text.lower()]
    geographies = [g for g in geography_keywords if g.lower() in text.lower()]

    extracted = []
    for fund in funds:
        entry = {
            "fund": fund,
            "ticket_size": ticket_info[0][1] if ticket_info else None,
            "fund_size": fund_size[0] if fund_size else None,
            "sectors": ", ".join(sectors),
            "geographies": ", ".join(geographies),
            "stage": ", ".join(stages),
            "source": url,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        extracted.append(entry)
    return extracted

# -------------------- MODULE 3: DATABASE --------------------

def init_db():
    conn = sqlite3.connect("investors.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS investors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund TEXT,
            ticket_size TEXT,
            fund_size TEXT,
            sectors TEXT,
            geographies TEXT,
            stage TEXT,
            source TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_data_to_db(entries):
    conn = sqlite3.connect("investors.db")
    c = conn.cursor()
    for e in entries:
        c.execute("""
            INSERT INTO investors (fund, ticket_size, fund_size, sectors, geographies, stage, source, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (e['fund'], e['ticket_size'], e['fund_size'], e['sectors'], e['geographies'], e['stage'], e['source'], e['timestamp']))
    conn.commit()
    conn.close()

# -------------------- MODULE 4: STREAMLIT UI --------------------

def streamlit_ui():
    st.title("Investor Discovery Platform")
    init_db()
    articles = fetch_articles_from_user_input()
    for article in articles:
        extracted = extract_data_from_text(article["text"], article["url"])
        insert_data_to_db(extracted)

    conn = sqlite3.connect("investors.db")
    df = pd.read_sql_query("SELECT * FROM investors", conn)

    sector_filter = st.multiselect("Filter by Sector", sorted(df["sectors"].dropna().unique()))
    geo_filter = st.multiselect("Filter by Geography", sorted(df["geographies"].dropna().unique()))

    if sector_filter:
        df = df[df["sectors"].str.contains('|'.join(sector_filter))]
    if geo_filter:
        df = df[df["geographies"].str.contains('|'.join(geo_filter))]

    df["source"] = df["source"].apply(lambda x: f"[Link]({x})")
    st.markdown("### Matched Investor Profiles")
    st.dataframe(df.drop(columns=["id"]), use_container_width=True)
    conn.close()

# -------------------- MAIN EXECUTION --------------------

if __name__ == "__main__":
    streamlit_ui()
