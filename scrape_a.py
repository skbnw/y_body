import os
import json
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import concurrent.futures
import boto3
import time
import logging
from botocore.exceptions import ClientError

# 環境変数からAWSの認証情報を取得
aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID']
aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']

# S3クライアントの作成
s3 = boto3.client('s3',
                  aws_access_key_id=aws_access_key_id,
                  aws_secret_access_key=aws_secret_access_key)

def minify_text(text):
    text = text.replace('\n', '\\n')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fetch_full_article(url):
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
        except requests.RequestException as e:
            if is_first_page:
                print(f"Error fetching data from {current_url}: {e}")
                return None, None
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

        time.sleep(3)

    return minify_text(full_text), json_ld_data


def save_article_as_json(url, media_en, progress):
    if url in progress:
        print(f"Article already processed: {url}")
        return

    article_text, json_ld_data = fetch_full_article(url)

    if json_ld_data:
        meta_data = {
            "headline": json_ld_data.get("headline"),
            "mainEntityOfPage": json_ld_data.get("mainEntityOfPage", {}).get("@id"),
            "image": json_ld_data.get("image"),
            "datePublished": json_ld_data.get("datePublished"),
            "dateModified": json_ld_data.get("dateModified"),
            "author": json_ld_data.get("author", {}).get("name"),
            "media_en": media_en
        }

        output_data = {"meta": meta_data, "body": minify_text(article_text)}

        if 'datePublished' in json_ld_data:
            date_published = json_ld_data['datePublished']
            date_obj = datetime.fromisoformat(date_published.rstrip('Z'))
            tokyo_timezone = pytz.timezone('Asia/Tokyo')
            date_obj_tokyo = date_obj.astimezone(tokyo_timezone)
            folder_name = date_obj_tokyo.strftime('%Y_%m%d')
            formatted_date = date_obj_tokyo.strftime('%Y_%m%d_%H%M')
            article_id = url.split('/')[-1]
            filename = f"{formatted_date}_{media_en}_{article_id}.json"

            if not os.path.exists(folder_name):
                os.makedirs(folder_name)

            file_path = os.path.join(folder_name, filename)

            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(output_data, file, ensure_ascii=False, indent=2)
              
            # S3にアップロード
            s3_key = os.path.join(folder_name, filename)
            upload_to_s3(file_path, "ynews-articles", s3_key)

            # ローカルファイルの削除
            os.remove(file_path)

            progress.add(url)
            with open('progress.json', 'w', encoding='utf-8') as progress_file:
                json.dump(list(progress), progress_file)
            print(f"File saved and progress updated for {url}")
    else:
        print(f"JSON-LD data not found or invalid for URL: {url}")

def process_url(row):
    media_en = row['media_en']
    base_url = row['url']
    group = row['group']

    # 空のリストを初期状態として設定
    article_links = []

    if group == 'b':
        has_more_pages = True
        current_page = 1
        while has_more_pages:
            print(f"Fetching page {current_page} of {base_url}")
            response = requests.get(base_url, params={'page': current_page})
            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.select('li > a:has(div.newsFeed_item_text)')
            if not articles:
                break

            for article in articles:
                link = article.get('href')
                if link:
                    article_links.append(link)

            current_page += 1

    # ここでリスト（空のリストも含む）を返す
    return [(link, media_en) for link in article_links]

def download_from_s3(bucket, object_name, file_path):
    try:
        s3.download_file(bucket, object_name, file_path)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def upload_to_s3(file_path, bucket, object_name=None):
    if object_name is None:
        object_name = os.path.basename(file_path)

    try:
        s3.upload_file(file_path, bucket, object_name)
    except boto3.exceptions.S3UploadFailedError as e:
        logging.error(e)
        return False
    return True

if __name__ == "__main__":
    # progress.jsonの読み込み
    progress_file_path = 'progress.json'
    progress_s3_key = 'progress.json'
    if download_from_s3('ynews-articles', progress_s3_key, progress_file_path):
        with open(progress_file_path, 'r', encoding='utf-8') as file:
            progress = set(json.load(file))
    else:
        progress = set()

    # その他の処理...

    # progress.jsonの保存とアップロード
    with open(progress_file_path, 'w', encoding='utf-8') as file:
        json.dump(list(progress), file)
    upload_to_s3(progress_file_path, 'ynews-articles', progress_s3_key)

    # メインスクリプトの実行
    csv_file_path = 'url/media_url_group.csv'
    urls_df = pd.read_csv(csv_file_path)

    # URLリストの生成と処理
    all_urls = []
    for index, row in urls_df.iterrows():
        all_urls.extend(process_url(row))

    # ThreadPoolExecutorを使用して並行処理
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(save_article_as_json, url, media_en, progress): (url, media_en) for url, media_en in all_urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url, media_en = future_to_url[future]
            try:
                future.result()
                print(f"Completed processing {url}")
            except Exception as e:
                print(f"{url} processing generated an exception: {e}")
