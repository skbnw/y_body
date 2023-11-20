from datetime import datetime, timedelta
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import pytz
import re
import os
import time

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
        "mainEntityOfPage": json_ld_data.get("mainEntityOfPage",
                                             {}).get("@id"),
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

      print(f"File saved as {file_path}")
      progress.add(url)
      with open('progress.json', 'w', encoding='utf-8') as progress_file:
        json.dump(list(progress), progress_file)
      print(f"File saved and progress updated for {url}")
  else:
    print(f"JSON-LD data not found or invalid for URL: {url}")


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
  group = row["group"]
  media_en = row['media_en']
  base_url = row['url']
  params = {'year': year, 'month': month, 'day': day, 'page': 1}
  article_links = []
  
  if group in ["a"]:
      continue

  # ニュース記事のリンクを収集する
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

  # 収集したリンクから記事を保存する
  for link in article_links:
    save_article_as_json(link, media_en, progress)

# 進行状況をJSONファイルに保存
with open('progress.json', 'w', encoding='utf-8') as progress_file:
  json.dump(list(progress), progress_file)
