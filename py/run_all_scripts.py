import time
import subprocess
import os
import sys

# 実行するPythonスクリプトのリスト
scripts = [
    # "file-g01.py",
    # "file-g02.py",
    # "file-g03.py",
    "file-g04.py",
    # "file-g05.py",
    # "file-g06.py",
    # "file-g07.py",
    # "file-g08.py",
    # "file-g09.py",
    # "file-g10.py",
    # "file-g11.py",
    # "file-g12.py",
    # "file-g13.py",
    # "file-g14.py",
    # "file-g15.py",
    # "file-g16.py",
]

# venvのpythonパス
python_exe = r"C:\Users\user\Documents\Github\Project_NewsDB\venv\Scripts\python.exe"

# 各スクリプトを順次実行
for script in scripts:
    try:
        print(f"Running {script}...", flush=True)
        # 2026-02-24を対象に実行
        subprocess.run([python_exe, f"py/{script}"], check=True)
        print(f"Finished {script}. Waiting for 5 seconds...", flush=True)
        time.sleep(5)  # 5秒待機
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running {script}: {e}", flush=True)
        # 次のスクリプトに進む
        continue

