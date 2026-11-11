import os
import sys
import re
import time
import json
import shutil
import datetime
import subprocess
import html as html_lib
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

VAULT_PAT = os.environ.get("VAULT_PAT")
if not VAULT_PAT:
    print("[ERROR] VAULT_PAT environment variable is required.")
    sys.exit(1)

VAULT_BASE_URL = f"https://x-access-token:{VAULT_PAT}@github.com/parshant65-lang"
BUFFER_DIR = "local_fe_buffer"
TEMP_VAULT_DIR = "vault_sync_tmp"

SESSION_MAX_SECONDS = 5 * 3600 + 30 * 60   # 5.5 Hours continuous session
PUSH_INTERVAL_SECONDS = 900                 # Push every 15 Minutes
BATCH_PAGES = 5                             # Concurrently fetch 5 pages per cycle
MAX_WORKERS = 5                             # 5 parallel HTTP threads
PER_PAGE = 100                              # 100 articles per page

VOLUMES = [
    {"vol": 1, "repo": "financial-express-vault-1", "start": 1, "end": 3000},
    {"vol": 2, "repo": "financial-express-vault-2", "start": 3001, "end": 6000},
    {"vol": 3, "repo": "financial-express-vault-3", "start": 6001, "end": 9102}
]

def clean_html(raw_html):
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", "", raw_html)
    clean = html_lib.unescape(clean)
    return " ".join(clean.split())

def determine_active_volume_and_checkpoint():
    """Finds current volume and page from vaults."""
    for v in VOLUMES:
        repo_name = v["repo"]
        v_url = f"{VAULT_BASE_URL}/{repo_name}.git"
        if os.path.exists(TEMP_VAULT_DIR):
            shutil.rmtree(TEMP_VAULT_DIR, ignore_errors=True)
        try:
            subprocess.run(["git", "clone", "--depth", "1", v_url, TEMP_VAULT_DIR], check=True, capture_output=True)
            cp_path = os.path.join(TEMP_VAULT_DIR, "checkpoint.json")
            if os.path.exists(cp_path):
                with open(cp_path, "r") as f:
                    cp = json.load(f)
                curr_p = cp.get("current_page", v["start"])
                if curr_p <= v["end"]:
                    print(f"[TARGET] Selected Volume {v['vol']} ({repo_name}) at Page {curr_p}")
                    shutil.rmtree(TEMP_VAULT_DIR, ignore_errors=True)
                    return v, cp
        except Exception as e:
            print(f"[WARN] Error inspecting {repo_name}: {e}")
        finally:
            if os.path.exists(TEMP_VAULT_DIR):
                shutil.rmtree(TEMP_VAULT_DIR, ignore_errors=True)

    # Default to Volume 1
    return VOLUMES[0], {"current_page": 1, "total_articles": 0}

def fetch_page(page_num):
    url = f"https://www.financialexpress.com/wp-json/wp/v2/posts?per_page={PER_PAGE}&page={page_num}&_fields=id,date,link,title,content"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=18) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if not isinstance(data, list):
                return page_num, []
            
            clean_articles = []
            for p in data:
                raw_c = p.get("content", {}).get("rendered", "")
                fe_paras = re.findall(r'<p class=["\x27]wp-block-paragraph["\x27][^>]*>(.*?)</p>', raw_c, re.DOTALL)
                if not fe_paras:
                    fe_paras = re.findall(r'<p[^>]*>(.*?)</p>', raw_c, re.DOTALL)
                
                clean_paras = []
                for para in fe_paras:
                    c = clean_html(para)
                    if len(c) > 30 and not any(skip in c.lower() for skip in ["subscribe", "newsletter", "advertisement", "all rights reserved"]):
                        clean_paras.append(c)

                clean_articles.append({
                    "id": p.get("id"),
                    "date": p.get("date"),
                    "title": clean_html(p.get("title", {}).get("rendered", "")),
                    "link": p.get("link"),
                    "word_count": sum(len(x.split()) for x in clean_paras),
                    "paragraphs": clean_paras
                })
            return page_num, clean_articles
    except Exception as e:
        print(f"[FETCH ERROR] Page {page_num}: {e}")
        return page_num, None

def push_buffer_to_vault(active_vol, checkpoint, buffered_pages):
    if not buffered_pages:
        print("[SYNC] Buffer empty. Nothing to push.")
        return

    repo_name = active_vol["repo"]
    v_url = f"{VAULT_BASE_URL}/{repo_name}.git"

    if os.path.exists(TEMP_VAULT_DIR):
        shutil.rmtree(TEMP_VAULT_DIR, ignore_errors=True)

    try:
        print(f"[SYNC] Cloning {repo_name} for sync...")
        subprocess.run(["git", "clone", "--depth", "1", v_url, TEMP_VAULT_DIR], check=True, capture_output=True)

        data_articles_dir = os.path.join(TEMP_VAULT_DIR, "data", "articles")
        os.makedirs(data_articles_dir, exist_ok=True)

        total_new_articles = 0
        min_p = min(buffered_pages.keys())
        max_p = max(buffered_pages.keys())

        for p_num, arts in buffered_pages.items():
            if not arts:
                continue
            # Partition into year/month folder based on first article's date
            try:
                dt_str = arts[0].get("date", "")
                dt = datetime.datetime.fromisoformat(dt_str)
                sub_folder = os.path.join(data_articles_dir, f"{dt.year:04d}", f"{dt.month:02d}")
            except Exception:
                sub_folder = os.path.join(data_articles_dir, "archive")
            os.makedirs(sub_folder, exist_ok=True)

            out_file = os.path.join(sub_folder, f"page_{p_num:05d}.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(arts, f, ensure_ascii=False, indent=1)
            total_new_articles += len(arts)

        # Update checkpoint
        checkpoint["current_page"] = max_p + 1
        checkpoint["total_articles"] = checkpoint.get("total_articles", 0) + total_new_articles
        checkpoint["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with open(os.path.join(TEMP_VAULT_DIR, "checkpoint.json"), "w") as f:
            json.dump(checkpoint, f, indent=2)

        # Commit and push
        subprocess.run(["git", "config", "user.name", "GitHub Action Runner"], cwd=TEMP_VAULT_DIR, check=True)
        subprocess.run(["git", "config", "user.email", "actions@github.com"], cwd=TEMP_VAULT_DIR, check=True)
        subprocess.run(["git", "add", "."], cwd=TEMP_VAULT_DIR, check=True)

        msg = f"[FE-HARVEST] Sync pages {min_p}-{max_p} (+{total_new_articles} articles, Total: {checkpoint['total_articles']}) [skip ci]"
        subprocess.run(["git", "commit", "-m", msg], cwd=TEMP_VAULT_DIR, check=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=TEMP_VAULT_DIR, capture_output=True)
        res_push = subprocess.run(["git", "push", "origin", "main"], cwd=TEMP_VAULT_DIR, capture_output=True, text=True)
        
        if res_push.returncode == 0:
            print(f"[SYNC SUCCESS] ✅ Pushed {total_new_articles} articles (Pages {min_p}-{max_p}) to {repo_name}!")
            buffered_pages.clear()
        else:
            print(f"[SYNC PUSH ERROR] {res_push.stderr.strip()}")

    except Exception as e:
        print(f"[SYNC EXCEPTION] {e}")
    finally:
        if os.path.exists(TEMP_VAULT_DIR):
            shutil.rmtree(TEMP_VAULT_DIR, ignore_errors=True)

def main():
    print("=" * 60)
    print("🚀 FINANCIAL EXPRESS 9.1 LAKH ARTICLES ARCHIVE HARVESTER")
    print("=" * 60)

    start_time = time.time()
    last_push_time = time.time()
    buffered_pages = {}

    active_vol, checkpoint = determine_active_volume_and_checkpoint()
    current_page = checkpoint.get("current_page", 1)
    max_pages = 9102

    print(f"Starting Session at Page: {current_page} | Target: {active_vol['repo']}")

    while (time.time() - start_time) < SESSION_MAX_SECONDS:
        if current_page > max_pages:
            print("🏁 All 9,102 pages harvested! Archive complete!")
            break

        # Check if volume boundary reached
        if current_page > active_vol["end"]:
            print(f"📦 Volume {active_vol['vol']} cap reached (Page {current_page} > {active_vol['end']}). Pushing and switching...")
            push_buffer_to_vault(active_vol, checkpoint, buffered_pages)
            active_vol, checkpoint = determine_active_volume_and_checkpoint()

        batch_targets = list(range(current_page, min(current_page + BATCH_PAGES, active_vol["end"] + 1)))
        if not batch_targets:
            break

        print(f"Fetching Pages {batch_targets[0]} to {batch_targets[-1]}...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_page = {executor.submit(fetch_page, p): p for p in batch_targets}
            for future in as_completed(future_to_page):
                p_num, articles = future.result()
                if articles is not None:
                    buffered_pages[p_num] = articles
                    print(f"  ✓ Page {p_num}: {len(articles)} articles parsed")

        current_page = batch_targets[-1] + 1
        time.sleep(1.0) # Polite pacing

        # Check 15-minute push interval or buffer size
        if (time.time() - last_push_time) >= PUSH_INTERVAL_SECONDS or len(buffered_pages) >= 20:
            push_buffer_to_vault(active_vol, checkpoint, buffered_pages)
            last_push_time = time.time()

    # Final session push
    if buffered_pages:
        push_buffer_to_vault(active_vol, checkpoint, buffered_pages)

    print("Session complete. Triggering autonomous handover relay...")
    try:
        cmd = [
            "gh", "workflow", "run", "harvest.yml",
            "--repo", "parshant65-lang/financial-express-engine"
        ]
        subprocess.run(cmd, capture_output=True, env=dict(os.environ, GITHUB_TOKEN=VAULT_PAT))
        print("✅ Relay handover triggered!")
    except Exception as e:
        print(f"Relay trigger note: {e}")

if __name__ == "__main__":
    main()
