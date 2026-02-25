import time
import subprocess
import os

# 実行するPythonスクリプトのリスト
scripts = [
    "file-g01.py",
    "file-g02.py",
    "file-g03.py",
    "file-g04.py",
    "file-g05.py",
    "file-g06.py",
    "file-g07.py",
    "file-g08.py",
    "file-g09.py",
    "file-g10.py",
    "file-g11.py",
    "file-g12.py",
    "file-g13.py",
    "file-g14.py",
    "file-g15.py",
    "file-g16.py",
]

# venvのpythonパス
python_exe = r"C:\Users\user\Documents\Github\Project_NewsDB\venv\Scripts\python.exe"

# 各スクリプトを順次実行
for script in scripts:
    try:
        print(f"Running {script}...")
        # 2026-02-24を対象に実行 (引数が使えるスクリプトのみ)
        # file-g04.pyなどは引数対応しているが、他は未確認のため引数なしで実行(デフォルトが前日なら2026-02-24になる)
        subprocess.run([python_exe, f"py/{script}"], check=True)
        print(f"Finished {script}. Waiting for 5 seconds...")
        time.sleep(5)  # 5秒待機
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running {script}: {e}")
        # 次のスクリプトに進む
        continue

