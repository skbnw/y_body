import glob
import re
from pathlib import Path

replacements = {
    r'"news_link": "cDTGMJ"': r'"news_link": "sc-1gg21n8-0"',
    r'"content_div": "iiJVBF"': r'"content_div": "sc-278a0v-0"',
    r'"title_div": "dHAJpi"': r'"title_div": "sc-3ls169-0"',
    r'"time": "faCsgc"': r'"time": "sc-16vsoxb-1"'
}

files = glob.glob('py/file-g*.py')
for file_path in files:
    content = Path(file_path).read_text(encoding='utf-8')
    orig_content = content
    for pattern, replacement in replacements.items():
        content = content.replace(pattern, replacement)
    
    if content != orig_content:
        Path(file_path).write_text(content, encoding='utf-8')
        print(f"Updated {file_path}")
    else:
        print(f"No changes for {file_path}")
