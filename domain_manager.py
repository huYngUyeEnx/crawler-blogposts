# domain_manager.py
from urllib.parse import urlparse, urlunparse, urldefrag
from pathlib import Path

def load_domains(path: str) -> set[str]:
    p = Path(path)
    if not p.exists():
        return set()
    out = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "://" in s:
            s = urlparse(s).netloc
        if s.startswith("www."):
            s = s[4:]
        s = s.strip("/").lower()
        if s:
            out.add(s)
    return out

def get_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""

def is_same_domain(url: str, base_domain: str) -> bool:
    d = get_domain(url)
    if not d:
        return False
    return d == base_domain or d.endswith("." + base_domain)

def normalize_url(url: str) -> str:
    # bỏ fragment, chuẩn hoá nhỏ gọn để chống trùng
    url, _ = urldefrag(url)
    parts = list(urlparse(url))
    parts[0] = parts[0].lower() or "http"  # scheme
    parts[1] = parts[1].lower()           # netloc
    return urlunparse(parts)
