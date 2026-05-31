#!/usr/bin/env python3
"""note の「謎解き」関連記事を検索APIから収集する。

- note 検索API (api/v3/searches) を複数クエリ・sort=new で取得
- 直近 WINDOW_HOURS 時間に公開された記事だけ採用（rolling window）
- seen.json に既出の key は除外（重複防止）
- 記事ごとに詳細API (api/v3/notes/<key>) を叩いてハッシュタグ・本文抜粋を付与
- 出力: state/candidates_raw.json

依存は Python 標準ライブラリのみ（pip 不要）。
"""
import json
import os
import re
import sys
import time
import html
import datetime
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state")

# --- 設定（自由に調整可） ---
QUERIES = ["謎解き", "一枚謎", "自作謎"]   # 収集クエリ。広すぎる語（考察/暗号単体）は入れない
WINDOW_HOURS = 28                          # 直近この時間の公開記事を対象
SIZE = 20                                  # 1ページ件数
MAX_PAGES = 6                              # クエリごとの最大ページ（安全弁）
DETAIL_SLEEP = 0.4                         # 詳細API間のスリープ（礼儀）
MAX_DETAILS = 150                          # 詳細取得の上限
UA = "Mozilla/5.0 (personal nazo-collector; daily personal use)"
JST = datetime.timezone(datetime.timedelta(hours=9))


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def search(q, start):
    qs = urllib.parse.urlencode(
        {"context": "note", "q": q, "size": SIZE, "start": start, "sort": "new"}
    )
    return get_json(f"https://note.com/api/v3/searches?{qs}")


def parse_dt(s):
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        return None


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def load_seen():
    p = os.path.join(STATE, "seen.json")
    if os.path.exists(p):
        try:
            return set(json.load(open(p, encoding="utf-8")))
        except Exception:
            return set()
    return set()


def main():
    now = datetime.datetime.now(JST)
    cutoff = now - datetime.timedelta(hours=WINDOW_HOURS)
    seen = load_seen()
    found = {}  # key -> record

    for q in QUERIES:
        for page in range(MAX_PAGES):
            start = page * SIZE
            try:
                data = search(q, start)
            except Exception as e:
                print(f"[warn] search q={q} start={start}: {e}", file=sys.stderr)
                break
            notes = (((data.get("data") or {}).get("notes") or {}).get("contents")) or []
            if not notes:
                break
            stop = False
            for n in notes:
                pa = parse_dt(n.get("publish_at"))
                if pa and pa < cutoff:
                    stop = True  # sort=new なので以降は全部古い
                    continue
                key = n.get("key")
                if not key or key in seen or key in found:
                    continue
                found[key] = {
                    "key": key,
                    "title": n.get("name"),
                    "user": (n.get("user") or {}).get("urlname"),
                    "publish_at": n.get("publish_at"),
                    "like_count": n.get("like_count") or 0,
                    "comment_count": n.get("comment_count") or 0,
                    "query": q,
                }
            if stop:
                break
            time.sleep(0.3)

    out = []
    for i, (key, rec) in enumerate(found.items()):
        if i >= MAX_DETAILS:
            print(f"[warn] hit MAX_DETAILS={MAX_DETAILS}, skipping rest", file=sys.stderr)
            break
        try:
            dd = (get_json(f"https://note.com/api/v3/notes/{key}").get("data")) or {}
            tags = []
            # note 詳細API はハッシュタグを hashtag_notes[].hashtag.name に持つ
            for t in (dd.get("hashtag_notes") or dd.get("hashtags") or []):
                name = (t.get("hashtag") or {}).get("name") or t.get("name")
                if name:
                    tags.append(re.sub(r"^#", "", name))
            rec["hashtags"] = tags
            rec["url"] = dd.get("note_url") or f"https://note.com/{rec['user']}/n/{key}"
            rec["description"] = strip_html(dd.get("description"))[:300]
            rec["body_excerpt"] = strip_html(dd.get("body"))[:1500]
        except Exception as e:
            print(f"[warn] detail {key}: {e}", file=sys.stderr)
            rec["hashtags"] = []
            rec["url"] = f"https://note.com/{rec['user']}/n/{key}"
            rec["description"] = ""
            rec["body_excerpt"] = ""
        out.append(rec)
        time.sleep(DETAIL_SLEEP)

    os.makedirs(STATE, exist_ok=True)
    with open(os.path.join(STATE, "candidates_raw.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"collected {len(out)} articles (window={WINDOW_HOURS}h, queries={QUERIES})")


if __name__ == "__main__":
    main()
