import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import pandas as pd
import pytz
from datetime import datetime, timedelta
from yahoo_news_article_scraper import get_article_links, scrape_yahoo_news_article

def save_articles_to_csv(article_data, media_en, yesterday):
    folder_name = f"{yesterday.strftime('%Y_%m%d')}"
    try:
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
            print(f"Created directory: {folder_name}")
        filename = os.path.join(folder_name, f"{yesterday.strftime('%Y-%m%d')}-{media_en}.csv")
        df = pd.DataFrame(article_data)
        df.to_csv(filename, index=False)
        print(f"CSV file saved as {filename} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Number of articles saved: {len(article_data)}")
    except Exception as e:
        print(f"Error saving CSV: {e}")

# メインのスクレイピング処理
csv_file_path = 'url/url_group.csv'
urls_df = pd.read_csv(csv_file_path)

tokyo_timezone = pytz.timezone('Asia/Tokyo')
yesterday = datetime.now(tokyo_timezone) - timedelta(days=1)
year, month, day = yesterday.year, yesterday.month, yesterday.day

print(f"Fetching articles for date: {yesterday.strftime('%Y-%m-%d')}")

timeout_duration = 60

for index, row in urls_df.iterrows():
    if row['group'] != 'g01':
        continue

    media_en = row['media_en']
    media_jp = row['media_jp']
    base_url = row['url']
    print(f"Processing {media_en} ({media_jp})")
    params = {'year': year, 'month': month, 'day': day, 'page': 1}
    
    # 記事リンクを取得
    article_links = get_article_links(base_url, params, timeout_duration)
    if not article_links:
        print(f"No article links found for {media_en} on {yesterday.strftime('%Y-%m-%d')}")
        continue
    else:
        print(f"Article links found: {article_links}")

    print(f"Found {len(article_links)} total links")
    article_data = []

    # 並列処理で記事をスクレイピング
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_link = {executor.submit(scrape_yahoo_news_article, link, media_en, media_jp, timeout_duration): link for link in article_links}
        for future in as_completed(future_to_link):
            try:
                article_info = future.result()
                if article_info:
                    article_data.append(article_info)
                else:
                    print(f"Article scraping failed for {future_to_link[future]}")
            except Exception as e:
                print(f"Error processing link {future_to_link[future]}: {e}")

    # データが取得できているか確認
    if not article_data:
        print(f"No article data to save for {media_en} on {yesterday.strftime('%Y-%m-%d')}")
    else:
        save_articles_to_csv(article_data, media_en, yesterday)

print("Scraping process completed.")
