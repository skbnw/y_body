import random
import json
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import re
import time

# 特定の日付を指定
TARGET_DATE = datetime.strptime('2024/12/31', '%Y/%m/%d')

# スクレイピング対象グループ
TARGET_GROUPS = [
    'g01', 'g02', 'g03', 'g04',
    'g05', 'g06', 'g07', 'g08',
    'g09', 'g10', 'g11', 'g12',
    'g13', 'g14', 'g15', 'g16'
]

# HTML構造の定義
EXPECTED_CLASSES = {
    "news_link": "cDTGMJ",          # ニュースリンクのクラス
    "content_div": "iiJVBF",        # コンテンツ全体を含むdivのクラス
    "title_div": "dHAJpi",          # タイトルを含むdivのクラス
    "time": "faCsgc",               # 時間表示のクラス
    "article_body": "article_body"  # 記事本文のクラス
}

def create_save_directory(target_date):
    """
    保存ディレクトリを作成する。
    py フォルダの親ディレクトリに、指定した日付のフォルダを作成。
    """
    current_dir = Path(__file__).parent.parent  # py フォルダの親ディレクトリ
    save_dir = current_dir / target_date.strftime('%Y-%m%d')  # 例: 2024-1231
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir

def save_articles_to_csv(article_data, media_en, target_date):
    """記事データをCSVに保存する"""
    if not article_data:
        print(f"No articles to save for {media_en}. Skipping.")
        return

    save_dir = create_save_directory(target_date)  # 保存先ディレクトリを取得
    filename = f"{target_date.strftime('%Y%m%d')}-{media_en}.csv"  # ファイル名を設定
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

    try:
        df = pd.DataFrame(article_data)
        df = df[columns]
        df.to_csv(file_path, index=False, encoding="utf-8")
        print(f"Articles saved to {file_path}")
    except Exception as e:
        print(f"Error saving articles for {media_en}: {e}")

def fetch_full_article(url, timeout_duration=30):
    """記事の本文を取得する"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout_duration)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        script_tag = soup.find('script', type='application/ld+json')
        json_ld_data = json.loads(script_tag.string) if script_tag else {}
        article_body = soup.find('div', {'class': EXPECTED_CLASSES["article_body"]})
        return article_body.get_text(strip=True) if article_body else '', json_ld_data
    except Exception as e:
        print(f"Error fetching article {url}: {e}")
        return None, None

def get_yahoo_news_urls(base_url, target_date, timeout_duration=30):
    """Yahooニュースから指定日付の記事リンクを取得する"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    urls = []

    # ターゲット日付をURLパラメータに追加
    year = target_date.year
    month = target_date.month
    day = target_date.day

    # 日付をクエリパラメータに追加
    current_url = f"{base_url}?year={year}&month={month:02d}&day={day:02d}"
    print(f"Fetching articles from URL: {current_url}")

    try:
        response = requests.get(current_url, headers=headers, timeout=timeout_duration)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        news_items = soup.find_all("a", class_=re.compile(EXPECTED_CLASSES["news_link"]))

        if not news_items:
            print("No articles found on the specified date.")
            return urls

        print(f"Found {len(news_items)} articles.")
        for item in news_items:
            article_url = item.get('href')
            if article_url:
                print(f"Found article URL: {article_url}")
                urls.append(article_url)

    except Exception as e:
        print(f"Error while fetching articles from URL {current_url}: {e}")

    print(f"Total {len(urls)} articles found for date {target_date.strftime('%Y-%m-%d')}.\n")
    return urls

def process_group(group, urls_df, target_date):
    """グループごとの処理を行う"""
    print(f"\nProcessing group: {group}")
    group_data = urls_df[urls_df['group'] == group]

    if group_data.empty:
        print(f"No URLs found for group {group}. Skipping.")
        return

    for _, row in group_data.iterrows():
        media_en = row['media_en']
        media_jp = row['media_jp']
        base_url = row['url']

        print(f"Processing media: {media_en} ({media_jp}) from URL: {base_url}")
        article_links = get_yahoo_news_urls(base_url, target_date, timeout_duration=30)
        article_data = []

        for link in article_links:
            print(f"Fetching full article from: {link}")
            article_text, json_ld_data = fetch_full_article(link)
            if article_text and json_ld_data:
                print(f"Article fetched successfully. Length: {len(article_text)} characters.")
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

            # スリープを追加（1～2秒のランダムな待機時間）
            time_to_sleep = random.uniform(1, 2)
            print(f"Sleeping for {time_to_sleep:.2f} seconds before the next request.")
            time.sleep(time_to_sleep)

        save_articles_to_csv(article_data, media_en, target_date)

def main():
    """メインの処理"""
    try:
        print(f"Starting scraping for date: {TARGET_DATE.strftime('%Y-%m-%d')}")

        # 現在のスクリプトのディレクトリを基準に相対パスを設定
        current_dir = Path(__file__).parent
        csv_file_path = current_dir.parent / 'url' / 'url_group.csv'

        if not csv_file_path.exists():
            print(f"CSV file not found: {csv_file_path}")
            return

        print(f"CSV file found: {csv_file_path}")
        urls_df = pd.read_csv(csv_file_path)
        print(f"Loaded CSV with {len(urls_df)} rows.")

        for group in TARGET_GROUPS:
            process_group(group, urls_df, TARGET_DATE)

        print("\nAll processing completed!")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
