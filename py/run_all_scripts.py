import time
import subprocess

# 実行するPythonスクリプトをリスト化
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

# スクリプトを順次実行
for script in scripts:
    try:
        print(f"Running {script}...")
        subprocess.run(["python", f"y_body/py/{script}"], check=True)
        print(f"Finished {script}. Waiting for 5 minutes...")
        time.sleep(300)  # 5分待機
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running {script}: {e}")
        break
