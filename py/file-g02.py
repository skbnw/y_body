import json
import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import re
import time
import random

def minify_text(text):
    text = text.replace('\n', '\\n')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fetch_full_article(url, timeout_duration=30):
    full_text = ''
    json_ld_data = None
    current_page_num = 1
    is_first_page = True

    while True:
        current_url = f"{url}?page={current_page_num}"
        try:
            response = requests.get(current_url, timeout=10)
            if response.status_code == 404 and not is_first_page:
                break
            response.raise_for_status()
        except (requests.RequestException, requests.Timeout) as e:
            print(f"Error or timeout at {current_url}: {e}")
            break

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

        current_page_num += 1

    return minify_text(full_text), json_ld_data

def process_article_link(link, media_en, media_jp, timeout_duration):
    article_text, json_ld_data = fetch_full_article(link, timeout_duration)
    if article_text and json_ld_data:
        str_count = len(article_text)  # 文章の文字数をカウント
        return {
            "headline": json_ld_data.get("headline"),
            "mainEntityOfPage": json_ld_data.get("mainEntityOfPage", {}).get("@id"),
            "image": json_ld_data.get("image"),
            "datePublished": json_ld_data.get("datePublished"),
            "dateModified": json_ld_data.get("dateModified"),
            "author": json_ld_data.get("author", {}).get("name"),
            "media_en": media_en,
            "media_jp": media_jp,
            "str_count": str_count,  # 文字数を結果に追加
            "body": article_text
        }
    else:
        return None

def save_articles_to_csv(article_data, folder_name, media_en):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # 日本時間で前日の日付を取得
    tokyo_timezone = pytz.timezone('Asia/Tokyo')
    yesterday = datetime.now(tokyo_timezone) - timedelta(days=1)
    
    # ファイル名の形式を yyyy-mmdd-media_en.csv に修正
    filename = f"{yesterday.strftime('%Y-%m%d')}-{media_en}.csv"
    filepath = os.path.join(folder_name, filename)
    
    df = pd.DataFrame(article_data)
    df.to_csv(filepath, index=False)
    print(f"CSV file saved as {filepath}")


def get_article_links(base_url, params, timeout_duration=30):
    article_links = []
    current_page_num = 1
    params = params.copy()  # パラメータをコピーして使用

    while True:
        params['page'] = current_page_num
        try:
            response = requests.get(base_url, params=params, timeout=timeout_duration)
            if response.status_code == 404:
                break
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            links = [a['href'] for a in soup.select('a.newsFeed_item_link') if '/images/' not in a['href']]

            if not links:
                break

            article_links.extend(links)
            current_page_num += 1

            time.sleep(random.uniform(2, 5))  # リクエスト間にランダムな待機時間

        except (requests.RequestException, requests.Timeout) as e:
            print(f"Error or timeout at {base_url}: {e}")
            break

    return article_links

# 日付の設定
tokyo_timezone = pytz.timezone('Asia/Tokyo')
yesterday = datetime.now(tokyo_timezone) - timedelta(days=1)
year, month, day = yesterday.year, yesterday.month, yesterday.day
folder_name = yesterday.strftime('%Y_%m%d')

# 指定されたURLとメディア情報
base_url = "https://news.yahoo.co.jp/media/jij"
media_en = "jij"
media_jp = "時事通信"
timeout_duration = 30

params = {'year': year, 'month': month, 'day': day, 'page': 1}
article_links = get_article_links(base_url, params, timeout_duration)
article_data = []

for link in article_links:
    data = process_article_link(link, media_en, media_jp, timeout_duration)
    if data:
        article_data.append(data)

if article_data:
    save_articles_to_csv(article_data, folder_name, media_en)
else:
    print("No articles found.")
