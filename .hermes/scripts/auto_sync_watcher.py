# -*- coding: utf-8 -*-
"""文件监控自动同步 — 施工方案生成系统
监控 D:\fanben\施工方案生成系统 目录，检测文件变化后自动 git commit + push
"""
import os
import time
import subprocess
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ===== 配置 =====
WATCH_DIR = r"D:\fanben\施工方案生成系统"
TOKEN_PATH = r"C:\Users\12407\AppData\Local\Temp\gh_token.txt"
DEBOUNCE_SECONDS = 10
GITHUB_USER = "y1240741780-design"
GITHUB_REPO = "construction-plan-system"

# ===== 忽略模式 =====
IGNORE_PATTERNS = [
    ".git",
    "__pycache__",
    "输出",
    "output",
    ".docx",
    ".pdf",
]

def should_ignore(path):
    rel = os.path.relpath(path, WATCH_DIR)
    for pat in IGNORE_PATTERNS:
        if pat in rel:
            return True
    return False

class DebounceHandler(FileSystemEventHandler):
    def __init__(self):
        self._timer = None
        self._lock = threading.Lock()
    
    def on_any_event(self, event):
        if event.is_directory:
            return
        if should_ignore(event.src_path):
            return
        # 防抖：每次变化重置计时器
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(DEBOUNCE_SECONDS, self._sync)
            self._timer.start()
            print(f"[{time.strftime('%H:%M:%S')}] 检测到变化: {os.path.relpath(event.src_path, WATCH_DIR)}")
    
    def _sync(self):
        try:
            self._do_sync()
        except Exception as e:
            print(f"[ERROR] 同步失败: {e}")
    
    def _do_sync(self):
        os.chdir(WATCH_DIR)
        
        # 获取 token
        with open(TOKEN_PATH) as f:
            token = f.read().strip()
        
        # git add
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
        
        # 检查是否有变更
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if result.returncode == 0:
            print(f"[{time.strftime('%H:%M:%S')}] 无变更，跳过提交")
            return
        
        # git commit
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        subprocess.run(["git", "commit", "-m", f"自动备份: {timestamp}"], check=True, capture_output=True)
        
        # git push
        remote_url = f"https://x-access-token:{token}@github.com/{GITHUB_USER}/{GITHUB_REPO}.git"
        # 确保 remote 存在
        subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True, capture_output=True)
        subprocess.run(["git", "push"], check=True, capture_output=True)
        
        print(f"[{time.strftime('%H:%M:%S')}] ✅ 自动提交+推送完成")

if __name__ == "__main__":
    print(f"🔍 开始监控: {WATCH_DIR}")
    print(f"⏱  防抖时间: {DEBOUNCE_SECONDS}s")
    print(f"📦 目标仓库: {GITHUB_USER}/{GITHUB_REPO}")
    print("-" * 50)
    
    handler = DebounceHandler()
    observer = Observer()
    observer.schedule(handler, WATCH_DIR, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n🛑 监控已停止")
    observer.join()
