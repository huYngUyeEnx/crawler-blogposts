# crawl_blogspot.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, re, json
from urllib.parse import urljoin, urlparse
from pathlib import Path
import uuid
from bs4 import BeautifulSoup

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
            img = driver.find_element(By.CSS_SELECTOR, "div#site-header a img , div.site-branding a img, div#header-image img")
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
                if host.endswith(".wordpress.com"):
                    name = host.split(".wordpress.com")[0]
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
            email = email_tag.text.strip() or email_tag.get_attribute("href").strip()
    except:
        pass 

    # 2️⃣ Nếu không tìm thấy, fallback sang regex quét toàn trang
    if not email:
        try:
            html = driver.page_source
            m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", html)
            if m:
                email = m.group(0)
        except:
            pass
        
    # --- Description ---
    description = ""
    try:
        # 1️⃣ Thử lấy nội dung từ thẻ hiển thị
        el = driver.find_element(By.CSS_SELECTOR, "h2.site-description")
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

    editor = ""
    try:
        html = driver.page_source  # hoặc đoạn HTML bạn lưu sẵn
        soup = BeautifulSoup(html, "html.parser")
        edit = soup.select_one("p.attribution")
        if edit:
            editor = edit.get_text(strip=True)
    except:
        editor = ""

    info = ""
    try:
        html = driver.page_source  # hoặc đoạn HTML bạn lưu sẵn
        soup = BeautifulSoup(html, "html.parser")
        el = soup.select_one("p.copyright, div.site-info")
        if el:
            info = el.get_text(strip=True)
    except:
        info = ""

    text = soup.get_text("\n", strip=True)   # lấy toàn bộ text, ngăn dòng bằng \n

    phone = ""
    m = re.search(r"Số\s*điện\s*thoại:\s*([+()0-9\s\.-]{7,})", text, re.I)
    if m:
        raw = m.group(1)
        phone = re.sub(r"[^\d+]", "", raw) 
    
    address = ""
    ad = re.search(r"Địa\s*chỉ\s*:\s*(.+?)(?:\n|Zipcode|$)", text, re.I)
    if ad:
        address = ad.group(1).strip()   
    return {
        "domain":driver.current_url,
        "name":name,
        "description":  description,
        "license":  "",
        "inforCopyright":info,
        "editorInChief":  editor,
        "address":  address,
        "phone":  phone,
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
# title
    try:
        el = driver.find_element(By.CSS_SELECTOR, "h2.wp-block-post-title ,h1.entry-title, h1.post-title , div#content div.post h2 , h1.wp-block-post-title , div.title h2")
        title = el.text.strip()
    except: 
        pass
# datime
    try:
        date = driver.find_element(By.CSS_SELECTOR, "div.entry-meta a.entry-date, div.wp-block-post-date time ,time.published , time.entry-date , span.post-meta-date a , div#content p.date")
        publishTime = (date.text or "").strip()
    except:
        pass
# tác giả
    try:
        author = ""
        authors = driver.find_elements(
            By.CSS_SELECTOR,
            "div.entry-meta a.author ,p.wp-block-post-author__name, span.author.vcard a, span.post-meta-author a, div.entrytext p b, div.wp-block-post-author-name a, div.title small"
        )
        for a in authors:
            t = a.text.strip()
            # Bỏ qua nếu text rỗng hoặc dài hơn 4 từ
            if not t or len(t.split()) > 4:
                continue
            author = t
            break
    except:
        author = ""

# content và ảnh
    try:
        div = driver.find_element(By.CSS_SELECTOR, "div.entry-content , div.post-content , div.entrytext , div.entry")

        # 🟢 Lấy tất cả text trong các thẻ <p>
        paragraphs = div.find_elements(By.TAG_NAME, "p")
        content = "\n".join(p.text.strip() for p in paragraphs if p.text.strip())

        # 🟡 Lấy toàn bộ ảnh trong entry-content
        for img in div.find_elements(By.TAG_NAME, "img"):
            src = img.get_attribute("src")
            if src and src not in images:
                images.append(src)

    except:
        content = ""


    categories = []
    try:
        els = driver.find_elements(By.CSS_SELECTOR, "a[rel='tag'],a[rel='category tag']")
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

    description = ""

    # 1) Lấy mô tả trong nội dung bài (nếu có)
    try:
        el = driver.find_element(
            By.CSS_SELECTOR,
            "div.entry-content h4 strong, div.entry-content h2, "
            "div.entry-content h3 strong, div.post-content p strong"
        )
        txt = (el.text or "").strip()
        if txt:
            description = txt
    except:
        pass
    # 2) Fallback sang meta description (trong <head>)
    if not description:
        try:
            metas = driver.find_elements(
                By.CSS_SELECTOR,
                'meta[name="description"], meta[property="og:description"]'
            )
            for m in metas:
                des = (m.get_attribute("content") or "").strip()
                if des:
                    description = des
                    break
        except:
            pass

    # 3) Fallback cuối cùng: regex trong toàn trang
    if not description:
        try:
            html = driver.page_source
            m = re.search(r'<meta[^>]+(?:name="description"|property="og:description")[^>]+content="([^"]+)"', html, re.I)
            if m:
                description = m.group(1).strip()
        except:
            pass

    thumbnails = []
    video_urls = []

    iframes = driver.find_elements(By.CSS_SELECTOR, 'div.embed-youtube iframe[src*="youtube.com"], iframe[src*="youtu.be"]')

    for f in iframes:
        try:
            driver.switch_to.frame(f)
            
            # lấy thumbnail url trong style
            for el in driver.find_elements(By.CSS_SELECTOR, "div.ytp-cued-thumbnail-overlay-image[style]"):
                style = el.get_attribute("style") or ""
                match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                if match:
                    thumbnails.append(match.group(1).strip())

            # lấy video url
            for a in driver.find_elements(By.CSS_SELECTOR, 'a.ytp-title-link[href]'):
                href = (a.get_attribute("href") or "").strip()
                if href and href not in video_urls:
                    video_urls.append(href)
        finally:
            driver.switch_to.default_content()
    return {
        "dataSource": base_domain,
        "title":title,
        "url":driver.current_url,
        "author":author,
        "authorId":"",
        "publishedDate":publishTime,
        "description": description,
        "content":content,
        "contentImagesUrls":images,
        "categories": categories,
        "thumbnailUrl": thumbnails,
        "location": "",
        "videoUrl": video_urls
        }

def get_domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc

def is_same_domain(url: str, base_domain: str) -> bool:
    d = get_domain(url)
    return d == base_domain or d.endswith("." + base_domain)
# lấy link
def collect_links_on_page(driver, base_url: str, same_domain_only=True, max_links=200):
    hrefs, seen = [], set()
    scroll_to_load(driver)

    # Chỉ cần tìm các thẻ a trong bài viết có href đầy đủ
    for a in driver.find_elements(By.CSS_SELECTOR,
        "header.entry-header h1.entry-title a ,div.entry-inner-content header.entry-header h2.entry-title a , header.entry-header h2.entry-title a, div.wideposts div.title h2 a[href],h2.wp-block-post-title a[href] , h2.entry-title a[href], h1.entry-title a[href], article.post figure.post-image a[href], div.post h2 a[href]"):
        h = (a.get_attribute("href") or "").strip()
        if not h:
            continue

        # Giữ lại các link kiểu WordPress: /YYYY/MM/DD/slug/
        if re.search(r"/\d{4}/\d{2}/\d{2}/[A-Za-z0-9\-_%]+/?$", h):
            if h not in seen:
                seen.add(h)
                hrefs.append(h)

        if len(hrefs) >= max_links:
            break
    return hrefs
def find_next_page_url(driver, wait_secs=8):
    """
    Phát hiện next-page:
    - Nếu có URL (anchor hoặc <link rel="next">) -> trả về URL
    - Nếu là nút load-more (#infinite-handle) -> click và trả về True
    - Nếu không có gì -> False
    """
    try:
        WebDriverWait(driver, wait_secs).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        # Kéo xuống đáy để hiện thanh điều hướng
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.6)

        # 1) WordPress: <link rel="next" href="..."> trong <head>
        try:
            next_link = driver.find_element(By.CSS_SELECTOR, "link[rel='next'][href]")
            href = (next_link.get_attribute("href") or "").strip()
            if href.startswith(("http://", "https://")):
                print(f"🔗 next (head rel=next): {href}")
                return href
        except: 
            pass

        # 2) Anchor điều hướng phổ biến của WP
        next_selectors = [
            ".nav-previous a",
            ".bottomnavigation .alignleft a",
            ".wp-block-group .alignwide a.wp-block-query-pagination-next",
            ".post-navigation p a"
         ]
        for sel in next_selectors:
            anchors = driver.find_elements(By.CSS_SELECTOR, sel)
            for a in anchors:
                href = (a.get_attribute("href") or "").strip()
                if href.startswith(("http://", "https://")):
                    return href

        # 3) Nút load-more kiểu infinite scroll
        btns = driver.find_elements(By.CSS_SELECTOR, "div#infinite-handle span button")
        if btns:
            before = len(driver.find_elements(By.CSS_SELECTOR, "article, .post, .hentry, h2.entry-title"))
            btn = btns[0]
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            try:
                btn.click()
            except:
                driver.execute_script("arguments[0].click();", btn)

            WebDriverWait(driver, wait_secs * 2).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "article, .post, .hentry, h2.entry-title")) > before
            )
            time.sleep(1.2)
            print("🔁 Đã bấm nút load-more, thêm bài mới.")
            return True

        # Không có gì để đi tiếp
        return False

    except:
        return False


def go_next_page(driver, visited_pages: set, wait_secs=6):
    """Bấm nút Older posts để tải thêm, thay vì chuyển URL mới."""
    result = find_next_page_url(driver, wait_secs=wait_secs)
    if result:
        return True
    print("✅ Hết nút Older posts hoặc không tải thêm.")
    return False

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
def crawl_one_domain(driver, start_url: str, out_path: Path, on_record,
                     same_domain_only=True, max_links=200):
    """Dùng chung cho:
       1) Load-more/append (button)
       2) Pagination có URL
       + Trước khi quét link: luôn scroll full đến đáy cho tới khi không tăng nữa.
    """
    def normalize_start_url(s: str) -> str:
        s = s.strip()
        if "://" not in s:
            s = "https://" + s
        if not s.endswith("/"):
            s += "/"
        return s

    start_url = normalize_start_url(start_url)
    domain = get_domain(start_url)
    print(f"\n🌐 Bắt đầu crawl domain: {domain} ({start_url})")

    results = []
    seen_links = set()
    driver.get(start_url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    page_idx = 0
    visited_pages = set()

    while True:
        page_idx += 1
        cur_listing = driver.current_url.split("#", 1)[0]
        if cur_listing in visited_pages:
            print(f"🔁 Trang {cur_listing} đã xử lý, bỏ qua.")
            break
        visited_pages.add(cur_listing)

        print(f"\n📄 Trang listing {page_idx}: {cur_listing}")

        # ==== SCROLL FULL TRƯỚC KHI QUÉT LINK ====
        # cuộn cho tới khi chiều cao trang không tăng nữa (chặn vòng lặp bằng max_rounds)
        last_h = driver.execute_script("return document.body.scrollHeight")
        rounds = 0
        max_rounds = 60       # có thể chỉnh
        pause_secs = 1.0      # có thể chỉnh
        while rounds < max_rounds:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_secs)
            new_h = driver.execute_script("return document.body.scrollHeight")
            if new_h == last_h:
                break
            last_h = new_h
            rounds += 1
        # =========================================

        # 🧩 Lấy danh sách bài viết đang hiển thị sau khi đã scroll full
        links = collect_links_on_page(driver, cur_listing, same_domain_only, max_links)
        new_links = [u for u in links if u not in seen_links]
        if not new_links:
            print("ℹ️ Không còn link mới trên trang hiện tại.")

        # 🧩 Mở từng bài viết để lấy nội dung
        for i, link in enumerate(new_links, 1):
            print(f"   [{i}/{len(new_links)}] 👉 {link}")
            try:
                rec = open_article_in_new_tab_and_scrape(driver, link)
                seen_links.add(link)
                results.append(rec)
                if on_record:
                    on_record({"type": "content", **rec})
            except Exception as e:
                print(f"   🔴 Lỗi khi xử lý {link}: {e}")
        next_step = find_next_page_url(driver, wait_secs=10)

        if isinstance(next_step, str) and next_step.startswith(("http://", "https://")):
            driver.get(next_step)
            continue
        elif next_step is True:
            # Đã bấm nút load-more và append bài mới -> loop quay lại,
            # lần sau sẽ scroll full và quét tiếp.
            continue
        else:
            print("✅ Không còn trang hoặc nút để load thêm.")
            break

    print(f"\n✅ Hoàn tất crawl {domain} — Tổng cộng {len(results)} bài.")
