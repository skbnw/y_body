from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
import re
import random
import time
from datetime import datetime, timedelta
import pandas as pd
import requests
from bs4 import BeautifulSoup

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

    time.sleep(random.uniform(2, 5))

  return minify_text(full_text), json_ld_data


def process_article_link(link, media_en, media_jp, progress):
  if link in progress:
    return None

  article_text, json_ld_data = fetch_full_article(link)
  if json_ld_data:
    paragraphs = len(article_text.split('\n'))
    str_count = len(article_text)
    return {
        "headline": json_ld_data.get("headline"),
        "mainEntityOfPage": json_ld_data.get("mainEntityOfPage",
                                             {}).get("@id"),
        "image": json_ld_data.get("image"),
        "datePublished": json_ld_data.get("datePublished"),
        "dateModified": json_ld_data.get("dateModified"),
        "author": json_ld_data.get("author", {}).get("name"),
        "media_en": media_en,
        "media_jp": media_jp,
        "paragraphs": paragraphs,
        "str_count": str_count,
        "body": article_text
    }
  else:
    return None


def save_articles_to_csv(article_data, media_en, yesterday):
  folder_name = f"{yesterday.strftime('%Y_%m%d')}"
  if not os.path.exists(folder_name):
    os.makedirs(folder_name)

  filename = os.path.join(folder_name,
                          f"{yesterday.strftime('%Y_%m%d')}_{media_en}.csv")
  df = pd.DataFrame(article_data)
  df.to_csv(filename, index=False)
  print(
      f"CSV file saved as {filename} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
  )


if os.path.exists('progress.json'):
  with open('progress.json', 'r', encoding='utf-8') as progress_file:
    progress = set(json.load(progress_file))
else:
  progress = set()

csv_file_path = 'url/media_url_group.csv'
urls_df = pd.read_csv(csv_file_path)

yesterday = datetime.now() - timedelta(days=1)
year, month, day = yesterday.year, yesterday.month, yesterday.day

for index, row in urls_df.iterrows():
  if row['group'] != 'a':  # グループ 'a' のみを対象とする
    continue
  media_en = row['media_en']
  media_jp = row['media_jp']
  base_url = row['url']
  params = {'year': year, 'month': month, 'day': day, 'page': 1}
  article_links = []
  article_data = []

  while True:
    response = requests.get(base_url, params=params)
    if response.status_code != 200:
      break

    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.select('li > a:has(div.newsFeed_item_text)')
    for article in articles:
      link = article.get('href')
      if link:
        article_links.append(link)

    params['page'] += 1

  with ThreadPoolExecutor(max_workers=10) as executor:
    future_to_link = {
        executor.submit(process_article_link, link, media_en, media_jp,
                        progress): link
        for link in article_links
    }
    for future in as_completed(future_to_link):
      article_info = future.result()
      if article_info:
        article_data.append(article_info)
        progress.add(future_to_link[future])

  save_articles_to_csv(article_data, media_en, yesterday)

# 進捗ファイルの保存
with open('progress.json', 'w', encoding='utf-8') as progress_file:
  json.dump(list(progress), progress_file)
