import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.exceptions import Timeout, RequestException
import os
import re
import random
import time
from datetime import datetime, timedelta
import pandas as pd
import requests
from bs4 import BeautifulSoup
import pytz

# ニュース記事をコンパクトにする
def minify_text(text):
    text = text.replace('\n', '\\n')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# 記事の本文を取得する
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

# 記事リンクから情報を処理する
def process_article_link(link, media_en, media_jp, timeout_duration):
    if 'image/0000' in link:
        return None

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

# 記事データをCSVに保存する
def save_articles_to_csv(article_data, media_en, yesterday):
    folder_name = f"{yesterday.strftime('%Y_%m%d')}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    filename = os.path.join(folder_name, f"{yesterday.strftime('%Y-%m%d')}-{media_en}.csv")
    df = pd.DataFrame(article_data)
    df.to_csv(filename, index=False)
    print(f"CSV file saved as {filename} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Yahooニュースから記事リンクを取得する
def get_yahoo_news_urls(base_url, target_date, timeout_duration=30):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    urls = []
    page = 1
    
    while True:
        url = f"{base_url}?page={page}"
        try:
            response = requests.get(url, headers=headers, timeout=timeout_duration)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            news_items = soup.select('.newsFeed_item')
            if not news_items:
                break

            for item in news_items:
                date_time = item.find('time').text.strip()
                match = re.match(r'(\d+)/(\d+)\(.\) (\d+):(\d+)', date_time)
                if match:
                    month, day, hour, minute = map(int, match.groups())
                    article_date = datetime(2024, month, day, hour, minute)

                    if article_date.date() == target_date.date():
                        article_url = item.find('a')['href']
                        urls.append(article_url)
                    elif article_date.date() < target_date.date():
                        return urls
            page += 1

        except (requests.RequestException, requests.Timeout) as e:
            print(f"Error or timeout at {url}: {e}")
            break

    return urls

# メインのスクレイピング処理
csv_file_path = 'url/url_group.csv'
urls_df = pd.read_csv(csv_file_path)

tokyo_timezone = pytz.timezone('Asia/Tokyo')
yesterday = datetime.now(tokyo_timezone) - timedelta(days=1)
year, month, day = yesterday.year, yesterday.month, yesterday.day

for index, row in urls_df.iterrows():
    if row['group'] != 'g07':
        continue

    media_en = row['media_en']
    media_jp = row['media_jp']
    base_url = row['url']
    
    # 記事リンクを取得する
    article_links = get_yahoo_news_urls(base_url, yesterday)
    article_data = []

    # スクレイピングを並列処理で実行
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_link = {executor.submit(process_article_link, link, media_en, media_jp, 30): link for link in article_links}
        for future in as_completed(future_to_link):
            article_info = future.result()
            if article_info:
                article_data.append(article_info)

    # CSVに保存
    save_articles_to_csv(article_data, media_en, yesterday)
