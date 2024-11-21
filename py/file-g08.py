import random 
import json
from datetime import datetime, timedelta
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re
import time

# 作業日（実行日）の前日を設定
TARGET_DATE = datetime.now() - timedelta(days=1)

# スクレイピング対象グループを限定
TARGET_GROUPS = ['g08']  # 必要に応じてグループを追加

# HTML構造の定義
EXPECTED_CLASSES = {
    "news_link": "cDTGMJ",          # ニュースリンクのクラス
    "content_div": "iiJVBF",        # コンテンツ全体を含むdivのクラス
    "title_div": "dHAJpi",          # タイトルを含むdivのクラス
    "time": "faCsgc",               # 時間表示のクラス
    "article_body": "article_body"   # 記事本文のクラス
}

def create_save_directory(target_date):
    """保存ディレクトリを作成する"""
    save_dir = Path(target_date.strftime('%Y-%m%d'))  # フォーマット例: 2024-1120
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir

def save_articles_to_csv(article_data, media_en, target_date):
    """記事データをCSVに保存する"""
    if not article_data:
        return

    save_dir = create_save_directory(target_date)
    filename = f"{target_date.strftime('%Y%m%d')}-{media_en}.csv"
    file_path = save_dir / filename

    columns = [
        "headline",
        "mainEntityOfPage",
        "image",
        "datePublished",
        "dateModified",
        "author",
        "media_en",
        "media_jp",
        "str_count",
        "body",
        "images",
        "external_links"
    ]

    df = pd.DataFrame(article_data)
    df = df[columns]
    df.to_csv(file_path, index=False, encoding="utf-8")
    print(f"Articles saved as {file_path}")

def fetch_full_article(url, timeout_duration=30):
    """記事の本文を取得する"""
    full_text = ''
    json_ld_data = None
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout_duration)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        script_tag = soup.find('script', type='application/ld+json')
        if script_tag:
            try:
                json_ld_data = json.loads(script_tag.string)
                if not isinstance(json_ld_data, dict):
                    json_ld_data = {}
            except json.JSONDecodeError:
                json_ld_data = {}

        article_body = soup.find('div', {'class': EXPECTED_CLASSES["article_body"]})
        if article_body:
            full_text = article_body.get_text('\n', strip=True)

        return re.sub(r'\s+', ' ', full_text).strip(), json_ld_data
    except Exception as e:
        print(f"Error fetching article {url}: {e}")
        return None, None


def get_yahoo_news_urls(base_url, target_date, timeout_duration=30, max_pages=10):
    """Yahooニュースから複数ページの記事リンクを取得する"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    urls = []
    page = 1

    target_month = target_date.month
    target_day = target_date.day

    print(f"\nLooking for articles from: {target_date.strftime('%Y-%m-%d')}")

    while page <= max_pages:
        current_url = f"{base_url}?page={page}"
        try:
            # リクエストを送信
            response = requests.get(current_url, headers=headers, timeout=timeout_duration)
            response.raise_for_status()

            # ページの解析
            soup = BeautifulSoup(response.content, 'html.parser')

            # デバッグ情報の出力
            print(f"\nChecking page {page}")

            # 記事リンクの取得
            news_items = soup.find_all("a", class_=re.compile(EXPECTED_CLASSES["news_link"]))

            if not news_items:
                print(f"No news items found on page {page}, checking HTML structure...")
                break

            found_target_date = False
            found_older_date = False

            for item in news_items:
                time_element = item.find("time", recursive=True)
                if not time_element:
                    continue

                date_text = time_element.text.strip()
                print(f"Found date: {date_text}")  # デバッグ出力

                match = re.match(r'(\d+)/(\d+)\(.\) (\d+):(\d+)', date_text)
                if match:
                    month, day, hour, minute = map(int, match.groups())

                    if month == target_month and day == target_day:
                        article_url = item.get('href')
                        if article_url:
                            print(f"Found article: {article_url}")
                            urls.append(article_url)
                            found_target_date = True
                    elif month < target_month or (month == target_month and day < target_day):
                        found_older_date = True
                        print(f"Found older date: {month}/{day}")

            if found_older_date and not found_target_date:
                print("Found older articles, stopping search")
                return urls

            page += 1
            time.sleep(random.uniform(2, 4))

        except Exception as e:
            print(f"Error on page {page}: {str(e)}")
            break

    print(f"Total {len(urls)} URLs found for base URL: {base_url}")
    return urls



def process_group(group, urls_df, target_date):
    """グループごとの処理を行う"""
    print(f"Processing group: {group}")
    group_data = urls_df[urls_df['group'] == group]

    if group_data.empty:
        print(f"No URLs found for group {group}")
        return

    for _, row in group_data.iterrows():
        media_en = row['media_en']
        media_jp = row['media_jp']
        base_url = row['url']

        # target_date を明示的に渡す
        article_links = get_yahoo_news_urls(base_url, target_date, max_pages=10)
        article_data = []

        for link in article_links:
            article_text, json_ld_data = fetch_full_article(link)
            if article_text and json_ld_data:
                article_data.append({
                    "headline": json_ld_data.get("headline", ""),
                    "mainEntityOfPage": json_ld_data.get("mainEntityOfPage", {}).get("@id", ""),
                    "image": json_ld_data.get("image", ""),
                    "datePublished": json_ld_data.get("datePublished", ""),
                    "dateModified": json_ld_data.get("dateModified", ""),
                    "author": json_ld_data.get("author", {}).get("name", ""),
                    "media_en": media_en,
                    "media_jp": media_jp,
                    "str_count": len(article_text),
                    "body": article_text,
                    "images": [],
                    "external_links": []
                })

        save_articles_to_csv(article_data, media_en, target_date)


def main():
    """メインの処理"""
    print(f"Starting scraping for date: {TARGET_DATE.strftime('%Y-%m-%d')}")

    csv_file_path = 'url/url_group.csv'  # リポジトリ内の相対パス
    urls_df = pd.read_csv(csv_file_path)

    for group in TARGET_GROUPS:
        process_group(group, urls_df, TARGET_DATE)

    print("\nAll processing completed!")

if __name__ == "__main__":
    main()
