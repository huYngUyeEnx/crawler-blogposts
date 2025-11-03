# vitoquoc.py
from __future__ import annotations
import re, time
from pathlib import Path
from urllib.parse import urlparse, urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

FIXED_LABEL_PATHS = [
    "search/label/B%C3%ACnh%20lu%E1%BA%ADn",
    "search/label/Ch%C3%ADnh%20tr%E1%BB%8B%20-%20X%C3%A3%20h%E1%BB%99i",
    "search/label/Bi%C3%AAn%20gi%E1%BB%9Bi%20-%20Bi%E1%BB%83n%20%C4%91%E1%BA%A3o",
    "search/label/Th%E1%BA%BF%20Gi%E1%BB%9Bi",
    "search/label/Cu%E1%BB%99c%20s%E1%BB%91ng",
    "search/label/Th%E1%BA%BF%20gi%E1%BB%9Bi%20tr%E1%BA%BB",
    "search/label/v%C4%83n%20h%C3%B3a",
    "search/label/G%C3%B3c%20th%C6%B0%20gi%C3%A3n",
]
LABEL_CATEGORIES = {
    "search/label/B%C3%ACnh%20lu%E1%BA%ADn": "Bình Luận",
    "search/label/Ch%C3%ADnh%20tr%E1%BB%8B%20-%20X%C3%A3%20h%E1%BB%99i": "Chính trị - Xã hội",
    "search/label/Bi%C3%AAn%20gi%E1%BB%9Bi%20-%20Bi%E1%BB%83n%20%C4%91%E1%BA%A3o": "Biên giới - Biển đảo",
    "search/label/Th%E1%BA%BF%20Gi%E1%BB%9Bi": "Thế Giới",
    "search/label/Cu%E1%BB%99c%20s%E1%BB%91ng": "Cuộc sống",
    "search/label/Th%E1%BA%BF%20gi%E1%BB%9Bi%20tr%E1%BA%BB": "Thế giới trẻ",
    "search/label/v%C4%83n%20h%C3%B3a": "Văn hóa",
    "search/label/G%C3%B3c%20th%C6%B0%20gi%C3%A3n": "Góc thư giãn",
}
WAIT_SECS = 10

# ===================== SELECTORS =====================
SELECTOR_LIST_LINKS = (
    "h2.post-title a[href], h3.post-title a[href], "
    "div.post h2 a[href], h2 > a[href]"
)

# Nút sang trang cũ hơn (next)
NEXT_SELECTORS = [
    "a.blog-pager-older-link",
    "span.blog-pager-older-link a",
    ".blog-pager-older-link a",
    "a.older-link",
    "a.older-posts",
]

# ===================== HELPERS =====================
def _wait_body(driver, secs: int = WAIT_SECS):
    WebDriverWait(driver, secs).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

def _normalize_base(base_url: str) -> str:
    base_url = (base_url or "").strip()
    if not base_url:
        return ""
    if "://" not in base_url:
        base_url = "https://" + base_url
    if not base_url.endswith("/"):
        base_url += "/"
    return base_url

def _root_from_url(u: str) -> str:
    try:
        p = urlparse(u)
        return f"{p.scheme}://{p.netloc}/" if p.scheme and p.netloc else ""
    except:
        return ""

# ===================== CONTENT =====================
def extract_content(driver, *, label_url: str = "", category_name: str = "", data_source_root: str = "") -> dict:
    """
    Trả về schema chuẩn:
      dataSource, title, url, author, publishedDate, content, contentImagesUrls, categories
    """
    article_url = driver.current_url
    if not data_source_root:
        data_source_root = _root_from_url(label_url or article_url)

    if not category_name and label_url:
        # Nếu có mapping LABEL_CATEGORIES, dùng nó:
        try:
            path = urlparse(label_url).path
            for k, v in LABEL_CATEGORIES.items():
                if path.endswith(k):
                    category_name = v
                    break
        except:
            pass

    title = author = publishTime = ""
    content, images = "", []

    # --- title ---
    try:
        el = driver.find_element(By.CSS_SELECTOR, "h1, h2.post-title, h2.art-postheader, h1.entry-title, div.post h2")
        title = (el.text or "").strip()
    except:
        pass

    # --- date ---
    try:
        date = driver.find_element(By.CSS_SELECTOR, "div.time-view i, time.published, p.MsoNoSpacing span, abbr.published, div.postmeta-primary span.meta_date")
        publishTime = (date.text or "").strip()
    except:
        pass

    # --- content & images ---
    try:
        div = driver.find_element(By.CSS_SELECTOR, "div.post-body, div.post-info")
        content = (div.text or "").strip()
        for img in div.find_elements(By.TAG_NAME, "img"):
            src = img.get_attribute("src")
            if src and src not in images:
                images.append(src)
        try:
            # Tách theo dòng và lấy dòng cuối cùng có chữ
            lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
            if lines:
                last_line = lines[-1]
                if len(last_line.split()) <= 3:
                    author = last_line
        except:
            pass
    except:
        pass

    return {
        "dataSource": data_source_root,
        "title": title,
        "url": article_url,
        "author": author,
        "publishedDate": publishTime,
        "content": content,
        "contentImagesUrls": images,
        "categories": category_name or "",
    }

# ===================== LISTING HELPERS =====================
def _collect_links_on_listing(driver) -> list[str]:
    """Lấy các link bài từ trang listing/label hiện tại (lọc trùng trong trang)."""
    _wait_body(driver)
    links, seen = [], set()
    for a in driver.find_elements(By.CSS_SELECTOR, SELECTOR_LIST_LINKS):
        h = (a.get_attribute("href") or "").strip()
        if not h or not h.startswith("http"):
            continue
        if h not in seen:
            seen.add(h)
            links.append(h)
    return links

def _find_next_url(driver) -> str | None:
    """Tìm URL trang 'cũ hơn' (next) với nhiều biến thể selector."""
    for sel in NEXT_SELECTORS:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            href = (el.get_attribute("href") or "").strip()
            if href.startswith("http"):
                return href
        except:
            continue
    return None

# ===================== CRAWL 1 LABEL (URL tuyệt đối) =====================
def crawl_label(driver, label_url: str, category_name: str = "", on_record=None):
    driver.get(label_url)
    _wait_body(driver)
    results = []
    visited_listing = set()
    seen_links_global = set()
    page = 0

    while True:
        cur = driver.current_url.split("#", 1)[0]
        if cur in visited_listing: break
        visited_listing.add(cur); page += 1
        print(f"📄 Đang crawl trang{page}: {cur}")

        links = _collect_links_on_listing(driver)
        links = [u for u in links if u not in seen_links_global]
        for u in links: seen_links_global.add(u)
        print(f"  + {len(links)} bài")

        for i, link in enumerate(links, 1):
            try:
                listing = driver.current_window_handle
                driver.execute_script("window.open(arguments[0], '_blank');", link)
                WebDriverWait(driver, WAIT_SECS).until(lambda d: len(d.window_handles) > 1)
                newh = [h for h in driver.window_handles if h != listing][0]
                driver.switch_to.window(newh)

                _wait_body(driver)

                item = extract_content(
                    driver,
                    label_url=label_url,
                    category_name=category_name,
                    data_source_root=_root_from_url(label_url),
                )
                results.append(item)

                if on_record:
                    on_record(item)

            except Exception as e:
                print(f"   🔴 lỗi bài: {e}")
            finally:
                try:
                    driver.close(); driver.switch_to.window(listing)
                except:
                    pass

        nxt = _find_next_url(driver)
        if not nxt: print("✅ hết trang."); break
        driver.get(nxt)

def crawl_fixed_labels(driver, base_url: str, out_dir: Path | None = None,
                       on_record=None, max_pages_per_label: int = 100):
    """
    Ghép base_url + các path label cố định → lần lượt crawl từng label.
    """
    base = _normalize_base(base_url)
    label_urls = [urljoin(base, p) for p in FIXED_LABEL_PATHS]

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    for label_url in label_urls:
        category_name = LABEL_CATEGORIES.get(label_url.replace(base, "").strip("/"), "Unknown")
        crawl_label(
            driver,
            label_url,
            out_path = None,
            category_name=category_name,
            on_record=on_record,
            max_pages=max_pages_per_label
        )

# ===================== OVERRIDE: CRAWL TOÀN DOMAIN = labels =====================
def crawl_one_domain(driver, start_url: str, on_record=None, max_pages=500):
    """
    Được gọi bởi crawl_manager.py (mode=domain).
    Thay vì crawl homepage, HÀM NÀY CHUYỂN HƯỚNG sang crawl theo các label cố định.
    - start_url: domain gốc, vd: https://vitoquocvietnam2012.blogspot.com/
    - out_path: file mà crawl_manager kỳ vọng; ta sẽ dùng thư mục cha của nó để lưu per-label.
    """
    # Dùng flow labels, không crawl homepage
    crawl_fixed_labels(
        driver,
        base_url=start_url,
        out_dir= None,
        on_record=on_record,
        max_pages_per_label=max_pages
    )   

# === thêm vào cuối vitoquoc.py (ngay dưới crawl_fixed_labels) ===
def crawl_from_root(driver, root_url: str, out_dir: Path | None = None,
                    on_record=None, max_pages_per_label: int = 100):
    """
    Nhận domain chính (ví dụ https://vitoquocvietnam2012.blogspot.com/)
    rồi tự động crawl tất cả label cố định trong FIXED_LABEL_PATHS.
    """
    return crawl_fixed_labels(
        driver,
        base_url=root_url,
        out_dir=out_dir,
        on_record=on_record,
        max_pages_per_label=max_pages_per_label,
    )
