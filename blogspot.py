# crawl_blogspot.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, re, json
from urllib.parse import urljoin, urlparse
from pathlib import Path
import uuid
NEXT_SELECTORS = [
    "a.blog-pager-older-link",
    "div.separator a[href]",
    "a.older-link", "a.older-posts", "a#Blog1_blog-pager-older-link",
    "a[rel='next']", ".nav-links .next", ".nav-previous a", ".older-posts a",
    "a.next", "li.next a", ".pagination a.next", ".pagination .nav-previous a",
    "a[aria-label='Next']", "a[aria-label*='Older']", "a[title*='Older']", "a[title*='Trang sau']",
]

def scroll_to_load(driver, times=6, pause=1.0):
    last_h = driver.execute_script("return document.body.scrollHeight")
    for _ in range(times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(pause)
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h: break
        last_h = new_h

def extract_profile(driver, profile_name: str = "", profile_url: str = "") -> dict:
    job_id = 1 
    # info = {
    #     "name": url,
    #     "description": "",
    #     "license": None,
    #     "editor_in_chief": None,
    #     "address": None,
    #     "phone": None,
    #     "email": None,
    #     "infor_copyright": None,
    #     "jobId": job_id or str(uuid.uuid4()),
    #     "logo": None,
    # }

    if profile_url:
        driver.get(profile_url)

    else:
        driver.get(f"https://www.google.com/search?q={profile_name}")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(1)
    
    logo_url = ""
    try:
        # 1️⃣ Ưu tiên lấy logo ở phần header
        try:
            img = driver.find_element(By.CSS_SELECTOR, "div#header-inner img, a#Header1_headerimg img, div.Header img")
            logo_url = img.get_attribute("src") or ""
        except:
            pass

        # 2️⃣ Nếu chưa có, lấy URL từ style background-image
        if not logo_url:
            try:
                el = driver.find_element(By.CSS_SELECTOR, "div#header-inner, div.Header-inner")
                style_str = el.get_attribute("style") or ""
                m = re.search(r"url\(['\"]?(.*?)['\"]?\)", style_str)
                if m:
                    logo_url = m.group(1)
            except:
                pass

        # 3️⃣ Nếu vẫn chưa có, lấy ảnh trong widget Profile (phần sidebar)
        if not logo_url:
            try:
                img = driver.find_element(By.CSS_SELECTOR, "div.widget.Profile img.profile-img")
                logo_url = img.get_attribute("src") or ""
            except:
                pass

    except:
        print("⚠️ Không tìm thấy logo:")

    try:
        name = driver.find_element(By.TAG_NAME, "h1").text.strip()
    except:
        name = ""

    # 👉 Nếu không có <h1> hoặc text rỗng, fallback theo domain
    if not name:
        try:
            # Ưu tiên dùng profile_url, nếu trống thì lấy current_url
            u = (profile_url or driver.current_url or "").strip()
            if not u:
                name = profile_name
            else:
                # Nếu thiếu scheme thì thêm vào
                if "://" not in u:
                    u = "https://" + u

                host = (urlparse(u).hostname or "").lower()

                # Bỏ www. nếu có
                if host.startswith("www."):
                    host = host[4:]

                # Nếu là blogspot thì lấy phần trước .blogspot.com
                if host.endswith(".blogspot.com"):
                    name = host.split(".blogspot.com")[0]
                else:
                    # Nếu domain khác thì lấy nhãn đầu tiên
                    name = host.split(".")[0]

                # Giữ lại chữ, số, gạch ngang và gạch dưới
                name = re.sub(r"[^a-z0-9_-]", "", name)
                if not name:
                    name = profile_name
        except:
            name = profile_name


    email = ""
    try:
        # 1️⃣ Thử tìm thẻ <a href="mailto:...">
        email_tag = driver.find_element(By.CSS_SELECTOR, "a[href^='mailto']")
        if email_tag:
            email = email_tag.text.strip() or email_tag.get_attribute("href").replace("mailto:", "").strip()
    except:
        pass  # Không in gì cả nếu không có mailto

    # 2️⃣ Nếu không tìm thấy, fallback sang regex quét toàn trang
    if not email:
        try:
            html = driver.page_source
            m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html)
            if m:
                email = m.group(0)
        except:
            pass
        
    info = ""
    try:
        # Ưu tiên theo thứ tự:
        selectors = [
            "div#Attribution1 div.widget-content, div.widget-content div.addthis_toolbox",  # 1) Attribution / addthis
            "div#credit div.left, footer div.left",                                         # 2) credit / footer.left
        ]

        # Thử lần lượt hai nhóm selector trên
        for sel in selectors:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                txt = (el.text or "").strip()
                if txt:
                    info = txt
                    break
            if info:
                break

        # 3) Nếu vẫn chưa có, lấy <p> cuối cùng có text trong footer.art-footer
        if not info:
            ps = driver.find_elements(By.CSS_SELECTOR, "footer.art-footer div.art-footer-default p")
            # Duyệt từ cuối lên đầu, lấy thẻ <p> cuối cùng có text
            for p in reversed(ps):
                txt = (p.text or "").strip()
                if txt:
                    info = txt
                    break

    except:
        print("⚠️ Không lấy được footer:")
        info = ""

    # --- Description ---
    description = ""
    try:
        # 1️⃣ Thử lấy nội dung từ thẻ hiển thị
        el = driver.find_element(By.CSS_SELECTOR, "div.descriptionwrapper p.description span, div.header-widget p")
        description = (el.text or "").strip()
    except:
        pass

    # 2️⃣ Nếu không có, thử lấy từ <meta name="description">
    if not description:
        try:
            meta = driver.find_element(By.CSS_SELECTOR, 'meta[name="description"]')
            content = meta.get_attribute("content")
            if content:
                description = content.strip()
        except:
            pass

    # 3️⃣ Nếu vẫn không có, fallback sang selector khác (nếu bạn muốn)
    if not description:
        try:
            el = driver.find_element(By.CSS_SELECTOR, "p.description span")
            description = (el.text or "").strip()
        except:
            pass

    # --- Editor ---
    editor = ""
    try:
        # 🧩 Thử lấy tất cả các thẻ <a> trong Attribution hoặc khu vực widget-content
        anchors = driver.find_elements(
            By.CSS_SELECTOR,
            "div.widget.Attribution div.widget-content a, div.widget-content a[href*='theme']"
        )

        # Lọc text hợp lệ
        editor_links = [a.text.strip() for a in anchors if a.text.strip()]

        # Ghép thành chuỗi
        editor = ", ".join(editor_links)
    except Exception as e:
        print("⚠️ Không lấy được editor:", e)
        editor = ""



    return {
        "domain":driver.current_url,
        "name":name,
        "description":  description,
        "license":  "",
        "inforCopyright":info,
        "editorInChief":  editor,
        "address":  "",
        "phone":  "",
        "email":email,
        "jobId":str(uuid.uuid4()) or job_id,
        "logo":logo_url,

        }

def extract_content(driver) -> dict:
    title = author = publishTime = ""
    content, images = "", []
    cur_url = driver.current_url
    parsed = urlparse(cur_url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}/"

    try:
        el = driver.find_element(By.CSS_SELECTOR, "h3.post-title, h2.post-title, h2.art-postheader, h1.entry-title")
        title = el.text.strip()
    except: pass
    try:
        date = driver.find_element(By.CSS_SELECTOR, "h2.date-header, time.published, p.MsoNoSpacing span, abbr.published, div.postmeta-primary span.meta_date")
        publishTime = (date.text or "").strip()
    except: pass
    try:
        spans = driver.find_elements(By.CSS_SELECTOR, "span b span,b span, span span span,a b span span span b, b i span, b i a, strong font")
        for sp in spans:
            t = sp.text.strip()
            if 2 < len(t) < 50 and " " in t and not any(x in t.lower() for x in ["bình luận","comments","by","posted","email"]):
                author = t; break
    except: pass
    try:
        div = driver.find_element(By.CSS_SELECTOR, "div.post-body")
        content = (div.text or "").strip()
        for img in div.find_elements(By.TAG_NAME, "img"):
            src = img.get_attribute("src")
            if src and src not in images: images.append(src)
    except: pass

    categories = []
    try:
        els = driver.find_elements(By.CSS_SELECTOR, "a[rel='tag'], div.post-labels a")
        for el in els:
            t = (el.text or "").strip()
            if not t:
                continue
            # Một số theme ghi "tag1, tag2" trong cùng thẻ -> tách thêm
            parts = [p.strip() for p in t.split(",") if p.strip()]
            categories.extend(parts)
        # Khử trùng lặp, giữ thứ tự
        seen = set()
        categories = [c for c in categories if not (c in seen or seen.add(c))]
    except Exception:
        pass
    
    return {
        "dataSource": base_domain,
        "title":title,
        "url":driver.current_url,
        "author":author,
        "publishedDate":publishTime,
        "content":content,
        "contentImagesUrls":images,
        "categories": [tag.text.strip() for tag in driver.find_elements(By.CSS_SELECTOR, "a[rel='tag'], div.post-labels a") if tag.text.strip()]
        }

def get_domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc

def is_same_domain(url: str, base_domain: str) -> bool:
    d = get_domain(url)
    return d == base_domain or d.endswith("." + base_domain)

def collect_links_on_page(driver, base_url: str, same_domain_only=True, max_links=200):
    base_domain = get_domain(base_url)
    hrefs, seen = [], set()
    scroll_to_load(driver)
    for a in driver.find_elements(By.CSS_SELECTOR, "h3.post-title a[href], h2.post-title a[href], h2.art-postheader a[href]"):
        h = (a.get_attribute("href") or "").strip()
        if not h: continue
        if not h.startswith("http"): h = urljoin(base_url, h)
        if "#" in h: h = h.split("#",1)[0]
        if same_domain_only and not is_same_domain(h, base_domain): continue
        if not re.search(r"/\d{4}/\d{2}/.+\.html$", h): continue
        if h not in seen:
            seen.add(h); hrefs.append(h)
        if len(hrefs) >= max_links: break
    return hrefs

def find_next_page_url(driver, wait_secs=6):
    WebDriverWait(driver, wait_secs).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(0.6)
    for sel in NEXT_SELECTORS:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in els:
                href = (el.get_attribute("href") or "").strip()
                if href.startswith(("http://","https://")): return href
        except: continue
    return None

def go_next_page(driver, visited_pages: set, wait_secs=6):
    next_url = find_next_page_url(driver, wait_secs=wait_secs)
    if not next_url or next_url in visited_pages: return False
    driver.get(next_url); return True

def open_article_in_new_tab_and_scrape(driver, url):
    listing_handle = driver.current_window_handle
    driver.execute_script("window.open(arguments[0], '_blank');", url)
    WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
    new_handle = [h for h in driver.window_handles if h != listing_handle][0]
    driver.switch_to.window(new_handle)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        scroll_to_load(driver, times=2, pause=0.5)
        item = extract_content(driver)
        return {"url": url, **item}
    finally:
        driver.close()
        driver.switch_to.window(listing_handle)

def crawl_one_domain(driver, start_url: str, out_path: Path,on_record, same_domain_only=True, max_links=200):
    def normalize_start_url(s: str) -> str:
        s = s.strip()
        if "://" not in s: s = "https://" + s
        if not s.endswith("/"): s += "/"
        return s

    start_url = normalize_start_url(start_url)
    domain = get_domain(start_url)
    print(f"\n🌐 Bắt đầu domain: {domain}  ({start_url})")

    results = []
    visited_listings, seen_links = set(), set()
    page_idx = 0

    driver.get(start_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    while True:
        cur_listing = driver.current_url.split("#", 1)[0]
        if cur_listing in visited_listings:
            print("🔁 Trang listing đã thăm, dừng:", cur_listing); break
        visited_listings.add(cur_listing)
        page_idx += 1
        print(f"\n📄 Trang listing {page_idx}: {cur_listing}")

        links = collect_links_on_page(driver, cur_listing, same_domain_only, max_links)
        new_links = [u for u in links if u not in seen_links]
        if not new_links:
            print("ℹ️ Không còn link mới → thử Next Page…")
            if not go_next_page(driver, visited_pages=visited_listings, wait_secs=10):
                print("✅ Hết pager hoặc không tìm thấy Next Page."); break
            continue

        for i, link in enumerate(new_links, 1):
            if link in seen_links:
                print(f"   ⚠️ Bỏ qua link trùng: {link}"); continue
            try:
                print(f"   [{i}/{len(new_links)}] 👉 {link}")
                rec = open_article_in_new_tab_and_scrape(driver, link)
                results.append(rec)
                seen_links.add(link)
                # out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"   🔴 Lỗi bài: {e}")
            rec = open_article_in_new_tab_and_scrape(driver, link)
            results.append(rec)
            if on_record:              # 👈 thêm dòng này
                on_record({"type": "content", **rec})
            # out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        if not go_next_page(driver, visited_pages=visited_listings, wait_secs=10):
            print("✅ Hết pager hoặc không tìm thấy Next Page."); break

    print(f"\n✅ Xong domain {domain}. Lưu {len(results)} bài vào {out_path.name}")
