from bs4 import BeautifulSoup
import re

def extract(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    
    print(f"--- Analyzing {filename} ---")
    
    # Try to find article links
    links = soup.find_all('a', href=re.compile(r'/articles/'))
    if links:
        link = links[0]
        print(f"Link class: {link.get('class')}")
        
        # Look for content div inside or near
        content_div = link.find('div', class_=re.compile(r'sc-278a0v-0')) or link.find('div', class_=re.compile(r'iiJVBF|bjaTyI'))
        if content_div:
            print(f"Content div class: {content_div.get('class')}")
            
            title_div = content_div.find('div', class_=re.compile(r'sc-3ls169-0')) or content_div.find('div', class_=re.compile(r'dHAJpi|fYdrKC'))
            if title_div:
                print(f"Title div class: {title_div.get('class')}")
            
            time_div = content_div.find('time') or content_div.find('div', class_=re.compile(r'sc-16vsoxb-1'))
            if time_div:
                if time_div.name == 'time':
                    parent = time_div.parent
                    print(f"Time parent class: {parent.get('class')}")
                else:
                    print(f"Time div class: {time_div.get('class')}")
    else:
        print("No article links found.")

extract('asahi_debug.html')
extract('debug_1.html')
