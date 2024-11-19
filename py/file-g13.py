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

# HTML構造の定義
EXPECTED_CLASSES = {
    "news_link": "sc-1gg21n8-0",    # ニュースリンクのクラス
    "title_container": "sc-3ls169-0", # タイトルコンテナのクラス
    "time": "sc-ioshdi-1",          # 時間表示のクラス
    "time_container": "sc-n3vj8g-0", # 時間コンテナのクラス
    "article_body": "article_body"    # 記事本文のクラス
}

class HTMLStructureError(Exception):
    """HTML構造の変更を検出した際に発生する例外"""
    pass

def minify_text(text):
    """ニュース記事をコンパクトにする"""
    text = text.replace('\n', '\\n')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fetch_full_article(url, timeout_duration=30):
    """記事の本文を取得する"""
    full_text = ''
    json_ld_data = None
    current_page_num = 1
    is_first_page = True
    start_time = datetime.now()
    images = []
    links = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    while True:
        current_url = f"{url}?page={current_page_num}"
        try:
            response = requests.get(current_url, headers=headers, timeout=10)
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

        article_body = soup.find('div', {'class': EXPECTED_CLASSES["article_body"]})
        if article_body:
            full_text += '\n' + article_body.get_text('\n', strip=True)
            images.extend([img['src'] for img in article_body.find_all('img') if img.get('src')])
            links.extend([a['href'] for a in article_body.find_all('a') if a.get('href')])

        current_page_num += 1
        time.sleep(random.uniform(2, 5))

    return minify_text(full_text), json_ld_data, images, links

def validate_html_structure(soup):
    """HTML構造を検証する"""
    news_items = soup.find_all("a", class_=re.compile(EXPECTED_CLASSES["news_link"]))
    if not news_items:
        raise HTMLStructureError(f"Expected class containing '{EXPECTED_CLASSES['news_link']}' for news links not found")
    return news_items

def get_yahoo_news_urls(base_url, target_date, timeout_duration=30):
    """Yahooニュースから記事リンクを取得する"""
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
            
            try:
                # 新しいHTML構造の検証と記事の取得
                news_items = validate_html_structure(soup)
            except HTMLStructureError as e:
                print(f"\n警告: HTMLの構造が変更されました！\nエラー内容: {str(e)}")
                break

            if not news_items:
                break

            for item in news_items:
                time_element = item.find('time', class_=re.compile(EXPECTED_CLASSES["time"]))
                if time_element:
                    date_time = time_element.text.strip()
                    match = re.match(r'(\d+)/(\d+)\(.\) (\d+):(\d+)', date_time)
                    if match:
                        month, day, hour, minute = map(int, match.groups())
                        article_date = datetime(2024, month, day, hour, minute)

                        if article_date.date() == target_date.date():
                            article_url = item.get('href')
                            if article_url:
                                urls.append(article_url)
                        elif article_date.date() < target_date.date():
                            return urls
            page += 1
            time.sleep(random.uniform(1, 3))  # 優しめのスクレイピング

        except (requests.RequestException, requests.Timeout) as e:
            print(f"Error or timeout at {url}: {e}")
            break

    return urls

def process_article_link(link, media_en, media_jp, timeout_duration):
    """記事リンクから情報を処理する"""
    if 'image/0000' in link:
        return None

    try:
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
    except Exception as e:
        print(f"Error processing article at {link}: {e}")
    return None

def save_articles_to_csv(article_data, media_en, yesterday):
    """記事データをCSVに保存する"""
    folder_name = f"{yesterday.strftime('%Y_%m%d')}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    filename = os.path.join(folder_name, f"{yesterday.strftime('%Y-%m%d')}-{media_en}.csv")
    df = pd.DataFrame(article_data)
    df.to_csv(filename, index=False)
    print(f"CSV file saved as {filename} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """メインのスクレイピング処理"""
    csv_file_path = 'url/url_group.csv'
    urls_df = pd.read_csv(csv_file_path)

    tokyo_timezone = pytz.timezone('Asia/Tokyo')
    yesterday = datetime.now(tokyo_timezone) - timedelta(days=1)

    for index, row in urls_df.iterrows():
        if row['group'] != 'g13':
            continue

        media_en = row['media_en']
        media_jp = row['media_jp']
        base_url = row['url']
        
        print(f"Processing {media_jp}...")
        
        try:
            # 記事リンクを取得する
            article_links = get_yahoo_news_urls(base_url, yesterday)
            if not article_links:
                print(f"No articles found for {media_jp}")
                continue

            article_data = []

            # スクレイピングを並列処理で実行
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_link = {
                    executor.submit(process_article_link, link, media_en, media_jp, 30): link 
                    for link in article_links
                }
                for future in as_completed(future_to_link):
                    try:
                        article_info = future.result()
                        if article_info:
                            article_data.append(article_info)
                    except Exception as e:
                        print(f"Error processing article: {e}")

            # CSVに保存
            if article_data:
                save_articles_to_csv(article_data, media_en, yesterday)
                print(f"Successfully processed {len(article_data)} articles for {media_jp}")
            else:
                print(f"No valid articles found for {media_jp}")

        except Exception as e:
            print(f"Error processing {media_jp}: {e}")
            continue

if __name__ == "__main__":
    main()
