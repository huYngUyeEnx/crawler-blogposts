# utils.py
import json
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

RESULT_PATH = Path(__file__).with_name("crawl_result.json")

def setup_driver(headless=True):
    """Khởi tạo Chrome WebDriver"""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,2000")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)

def append_result_pretty(entry: dict, path: Path = RESULT_PATH):
    """Ghi kết quả crawl vào file JSON (xuống dòng, có timestamp)"""
    data = dict(entry)
    data.setdefault("_saved_at", datetime.utcnow().isoformat() + "Z")

    # Đọc file hiện có (nếu chưa thì tạo mảng rỗng)
    if path.exists():
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(content, list):
                content = []
        except:
            content = []
    else:
        content = []

    # Ghi thêm record mới
    content.append(data)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
