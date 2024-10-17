import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime

def get_article_links(base_url, params, timeout_duration=60):
    article_links = []
    current_page_num = 1
    params = params.copy()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    while True:
        params['page'] = current_page_num
        try:
            print(f"Fetching links from {base_url} with params: {params}")
            response = requests.get(base_url, params=params, headers=headers, timeout=timeout_duration)
            if response.status_code == 404:
                print(f"Page not found (404) for {base_url}")
                break
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            links = [a['href'] for a in soup.select('a.newsFeed_item_link') if '/images/' not in a['href']]
            links = [link for link in links if 'image/0000' not in link]

            print(f"Found {len(links)} links on page {current_page_num}")

            if not links:
                print(f"No links found on page {current_page_num}. Stopping.")
                break

            article_links.extend(links)
            current_page_num += 1

            time.sleep(random.uniform(2, 5))

        except requests.RequestException as e:
            print(f"Error or timeout at {base_url}: {e}")
            if 'response' in locals():
                print(f"Response status code: {response.status_code}")
                print(f"Response content: {response.text[:500]}")
            break

    return article_links

def scrape_yahoo_news_article(url, media_en, media_jp, timeout_duration=60):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"Scraping article: {url}")
        response = requests.get(url, headers=headers, timeout=timeout_duration)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.select_one('h1.headline').text.strip() if soup.select_one('h1.headline') else ''
        content = ' '.join([p.text for p in soup.select('div.article_body p:not(.readmore)')])
        date_str = soup.select_one('time')['datetime'] if soup.select_one('time') else ''
        date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d %H:%M:%S") if date_str else ''
        
        article_info = {
            'title': title,
            'content': content,
            'date': date,
            'url': url,
            'media_en': media_en,
            'media_jp': media_jp
        }
        
        print(f"Successfully scraped article: {title}")
        return article_info
    
    except requests.RequestException as e:
        print(f"Error scraping article {url}: {e}")
        return None