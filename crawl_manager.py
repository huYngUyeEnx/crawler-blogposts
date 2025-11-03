# crawl_manager.py
import sys, importlib, json
from pathlib import Path
from utils import setup_driver, append_result_pretty

USAGE = """\
Cách dùng:
  python crawl_manager.py profile <domain_file_name> <url>
  python crawl_manager.py content <domain_file_name> <url>
  python crawl_manager.py domain  <domain_file_name> <url>

Ví dụ:
  python crawl_manager.py profile vitoquoc https://vitoquoc.blogspot.com/
  python crawl_manager.py content vitoquoc https://vitoquoc.blogspot.com/2025/10/bai-viet.html
  python crawl_manager.py domain  vitoquoc https://vitoquoc.blogspot.com/
"""

def main():
    if len(sys.argv) < 4:
        print(USAGE)
        sys.exit(1)

    mode = sys.argv[1].lower()       # profile / content / domain
    domain_file = sys.argv[2].lower()  # ví dụ: vitoquoc
    url = sys.argv[3]

    # import module domain
    try:
        mod = importlib.import_module(domain_file)
    except ModuleNotFoundError:
        print(f"❌ Không tìm thấy file {domain_file}.py")
        sys.exit(1)

    driver = setup_driver(headless=True)

    try:
        if mode == "profile":
            if hasattr(mod, "extract_profile"):
                res = mod.extract_profile(driver, profile_url=url)
                append_result_pretty(res)
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                print(f"❌ File {domain_file}.py không có hàm extract_profile")

        elif mode == "content":
            if hasattr(mod, "extract_content"):
                driver.get(url)
                res = mod.extract_content(driver)
                append_result_pretty(res)
                print(json.dumps(res, ensure_ascii=False, indent=2))
            else:
                print(f"❌ File {domain_file}.py không có hàm extract_content")

        elif mode == "domain":
            if hasattr(mod, "crawl_one_domain"):
                out_path = f"{domain_file}.json"
                mod.crawl_one_domain(driver, start_url=url, out_path=out_path, on_record=append_result_pretty)
            else:
                print(f"❌ File {domain_file}.py không có hàm crawl_one_domain")

        else:
            print(USAGE)
            sys.exit(1)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
