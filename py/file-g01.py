import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import pandas as pd
import pytz
from datetime import datetime, timedelta
from yahoo_news_article_scraper import get_article_links, scrape_yahoo_news_article

def save_articles_to_csv(article_data, media_en, yesterday):
    folder_name = f"{yesterday.strftime('%Y_%m%d')}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    filename = os.path.join(folder_name, f"{yesterday.strftime('%Y-%m%d')}-{media_en}.csv")
    df = pd.DataFrame(article_data)
    df.to_csv(filename, index=False)
    print(f"CSV file saved as {filename} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Number of articles saved: {len(article_data)}")

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
    article_links = get_article_links(base_url, params, timeout_duration)
    print(f"Found {len(article_links)} total links")
    article_data = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_link = {executor.submit(scrape_yahoo_news_article, link, media_en, media_jp, timeout_duration): link for link in article_links}
        for future in as_completed(future_to_link):
            article_info = future.result()
            if article_info:
                article_data.append(article_info)

    save_articles_to_csv(article_data, media_en, yesterday)