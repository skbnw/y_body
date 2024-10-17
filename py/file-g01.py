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
from yahoo_news_article_scraper import scrape_yahoo_news_article

def save_articles_to_csv(article_data, media_en, yesterday):
    folder_name = f"{yesterday.strftime('%Y_%m%d')}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    filename = os.path.join(folder_name, f"{yesterday.strftime('%Y-%m%d')}-{media_en}.csv")
    df = pd.DataFrame(article_data)
    df.to_csv(filename, index=False)
    print(f"CSV file saved as {filename} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def get_article_links(base_url, params, timeout_duration=30):
    article_links = []
    current_page_num = 1
    params = params.copy()

    while True:
        params['page'] = current_page_num
        try:
            response = requests.get(base_url, params=params, timeout=timeout_duration)
            if response.status_code == 404:
                break
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            links = [a['href'] for a in soup.select('a.newsFeed_item_link') if '/images/' not in a['href']]
            links = [link for link in links if 'image/0000' not in link]

            if not links:
                break

            article_links.extend(links)
            current_page_num += 1

            time.sleep(random.uniform(2, 5))

        except (requests.RequestException, requests.Timeout) as e:
            print(f"Error or timeout at {base_url}: {e}")
            break

    return article_links

# メインのスクレイピング処理
csv_file_path = 'url/url_group.csv'  # 相対パスに変更
urls_df = pd.read_csv(csv_file_path)

tokyo_timezone = pytz.timezone('Asia/Tokyo')
yesterday = datetime.now(tokyo_timezone) - timedelta(days=1)
year, month, day = yesterday.year, yesterday.month, yesterday.day

timeout_duration = 30

for index, row in urls_df.iterrows():
    if row['group'] != 'g01':
        continue

    media_en = row['media_en']
    media_jp = row['media_jp']
    base_url = row['url']
    params = {'year': year, 'month': month, 'day': day, 'page': 1}
    article_links = get_article_links(base_url, params, timeout_duration)
    article_data = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_link = {executor.submit(scrape_yahoo_news_article, link, media_en, media_jp, timeout_duration): link for link in article_links}
        for future in as_completed(future_to_link):
            article_info = future.result()
            if article_info:
                article_data.append(article_info)

    save_articles_to_csv(article_data, media_en, yesterday)