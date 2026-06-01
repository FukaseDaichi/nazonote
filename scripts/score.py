#!/usr/bin/env python3
"""機械的な“下ごしらえ”スコアで候補を並べ替え、AI(スキル)に渡す候補プールを用意する。

最終的な採点・選抜は AI(スキル nazo-digest) が行う。ここでのスコアはあくまで
- ノイズを下げて候補プールを良質にするための事前ヒント
- 学習タグ(weights_learned)を反映した“好み”の事前順位
であり、表示上の最終順位は AI の selection が優先される。

出力:
  state/candidates.json      … 全件（mech_score/rank 付き、スコア降順）
  state/candidates_top.json  … 上位 POOL_N 件（AIが内容確認する候補プール。本文抜粋・marker・meta付き）
  state/today.txt            … 本日の日付(JST, YYYY-MM-DD)。スキルが出力ファイル名に使う。
"""
import json
import os
import math
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state")

# --- 設定 ---
POOL_N = 40         # AIが内容確認する候補プールの件数（全体を広く見つつトークンを抑える）
W_RECENCY = 2.0
W_LIKE = 0.5
TITLE_FACTOR = 0.5
WINDOW_HOURS = 28
JST = datetime.timezone(datetime.timedelta(hours=9))


def load_json(p, default):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def marker_of(c):
    return f"<!-- key={c['key']} tags={','.join(c.get('hashtags') or [])} -->"


def meta_of(c):
    s = f"@{c.get('user', '')} · ❤{c.get('like_count', 0)} · {(c.get('publish_at') or '')[:16]}"
    ti = " ".join("#" + t for t in (c.get("hashtags") or [])[:6])
    return s + (f" · {ti}" if ti else "")


def main():
    cands = load_json(os.path.join(STATE, "candidates_raw.json"), [])
    base = load_json(os.path.join(STATE, "weights_base.json"), {})
    learned = load_json(os.path.join(STATE, "weights_learned.json"), {})

    combined = dict(base)
    for k, v in learned.items():
        combined[k] = combined.get(k, 0) + v

    now = datetime.datetime.now(JST)
    for c in cands:
        tags = c.get("hashtags") or []
        tag_score = sum(combined.get(t, 0) for t in tags)
        title = c.get("title") or ""
        title_score = TITLE_FACTOR * sum(w for kw, w in combined.items() if kw in title)
        rec = 0.0
        try:
            pa = datetime.datetime.fromisoformat(c["publish_at"])
            age_h = (now - pa).total_seconds() / 3600.0
            rec = W_RECENCY * max(0.0, 1.0 - age_h / WINDOW_HOURS)
        except Exception:
            pass
        like = W_LIKE * math.log1p(c.get("like_count") or 0)
        c["score"] = round(tag_score + title_score + rec + like, 2)

    cands.sort(key=lambda c: c["score"], reverse=True)
    for i, c in enumerate(cands):
        c["rank"] = i + 1
        c["pool"] = i < POOL_N

    with open(os.path.join(STATE, "candidates.json"), "w", encoding="utf-8") as f:
        json.dump(cands, f, ensure_ascii=False, indent=2)

    # AI候補プール（内容確認に必要な情報を全部入れる）
    top = []
    for c in cands:
        if not c.get("pool"):
            continue
        top.append({
            "key": c["key"],
            "title": c["title"],
            "url": c["url"],
            "user": c.get("user"),
            "like_count": c.get("like_count", 0),
            "publish_at": c.get("publish_at"),
            "hashtags": c.get("hashtags") or [],
            "description": c.get("description", ""),
            "body_excerpt": (c.get("body_excerpt", "") or "")[:500],
            "mech_score": c["score"],
            "meta": meta_of(c),
            "marker": marker_of(c),
        })
    with open(os.path.join(STATE, "candidates_top.json"), "w", encoding="utf-8") as f:
        json.dump(top, f, ensure_ascii=False, indent=2)

    with open(os.path.join(STATE, "today.txt"), "w", encoding="utf-8") as f:
        f.write(now.strftime("%Y-%m-%d"))

    print(f"scored {len(cands)} articles; AI候補プール {len(top)} 件 (POOL_N={POOL_N})")
    for c in cands[:8]:
        print(f"  pre#{c['rank']:>2} {c['score']:>6}  {(c['title'] or '')[:36]:36}  {c.get('hashtags', [])[:3]}")


if __name__ == "__main__":
    main()
