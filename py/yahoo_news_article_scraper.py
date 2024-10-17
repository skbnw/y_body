import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random
from datetime import datetime
from requests.exceptions import RequestException, Timeout

def minify_text(text):
    text = text.replace('\n', '\\n')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fetch_full_article(url, timeout_duration=30):
    full_text = ''
    json_ld_data = None
    current_page_num = 1
    is_first_page = True
    start_time = datetime.now()
    images = []
    links = []

    while True:
        current_url = f"{url}?page={current_page_num}"
        try:
            response = requests.get(current_url, timeout=10)
            if response.status_code == 404 and not is_first_page:
                break
            response.raise_for_status()
        except (RequestException, Timeout) as e:
            print(f"Error or timeout at {current_url}: {e}")
            return None, None, None, None

        if (datetime.now() - start_time).total_seconds() > timeout_duration:
            print(f"Total fetching time exceeded timeout at {current_url}")
            return None, None, None, None

        soup = BeautifulSoup(response.text, 'html.parser')
        if is_first_page:
            script_tag = soup.find('script', type='application/ld+json')
            if script_tag:
                try:
                    json_ld_data = json.loads(script_tag.string)
                    if not isinstance(json_ld_data, dict):
                        json_ld_data = {}
                except json.JSONDecodeError:
                    json_ld_data = {}
            is_first_page = False

        article_body = soup.find('div', {'class': 'article_body'})
        if article_body:
            full_text += '\n' + article_body.get_text('\n', strip=True)
            images.extend([img['src'] for img in article_body.find_all('img') if img.get('src')])
            links.extend([a['href'] for a in article_body.find_all('a') if a.get('href')])

        current_page_num += 1
        time.sleep(random.uniform(2, 5))

    return minify_text(full_text), json_ld_data, images, links

def process_article_link(link, media_en, media_jp, timeout_duration):
    article_text, json_ld_data, images, links = fetch_full_article(link, timeout_duration)
    if article_text and json_ld_data:
        str_count = len(article_text)
        return {
            "headline": json_ld_data.get("headline"),
            "mainEntityOfPage": json_ld_data.get("mainEntityOfPage", {}).get("@id"),
            "image": json_ld_data.get("image"),
            "datePublished": json_ld_data.get("datePublished"),
            "dateModified": json_ld_data.get("dateModified"),
            "author": json_ld_data.get("author", {}).get("name"),
            "media_en": media_en,
            "media_jp": media_jp,
            "str_count": str_count,
            "body": article_text,
            "images": images,
            "external_links": links
        }
    else:
        return None

# この関数を使用して記事をスクレイプします
def scrape_yahoo_news_article(url, media_en, media_jp, timeout_duration=30):
    return process_article_link(url, media_en, media_jp, timeout_duration)