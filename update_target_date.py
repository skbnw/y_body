import glob
import re
from pathlib import Path

# TARGET_DATE の更新パターン:
# 1. TARGET_DATE = datetime.now(JST) - timedelta(days=1) -> TARGET_DATE = datetime.now(JST)
# 2. TARGET_DATE = datetime.now() - timedelta(days=1) -> TARGET_DATE = datetime.now()

replacements = {
    r'TARGET_DATE = datetime\.now\(JST\) - timedelta\(days=1\)': r'TARGET_DATE = datetime.now(JST)',
    r'TARGET_DATE = datetime\.now\(\) - timedelta\(days=1\)': r'TARGET_DATE = datetime.now()'
}

files = glob.glob('py/file-g*.py')
for file_path in files:
    content = Path(file_path).read_text(encoding='utf-8')
    orig_content = content
    for pattern, replacement in replacements.items():
        # 正規表現を使用して置換
        content = re.sub(pattern, replacement, content)
    
    if content != orig_content:
        Path(file_path).write_text(content, encoding='utf-8')
        print(f"Updated TARGET_DATE in {file_path}")
    else:
        print(f"No changes for {file_path}")
