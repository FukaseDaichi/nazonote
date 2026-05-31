#!/usr/bin/env python3
"""candidates_raw.json に優先度スコアを付けて並べ替える。

score = w_recency*(新しさ)
      + Σ_tag ( weights_base[tag] + weights_learned[tag] )   ← ハッシュタグ
      + title_factor * Σ_kw ( タイトル中のキーワード )
      + w_like * log1p(like_count)

出力:
  state/candidates.json      … 全件（rank/score/score_detail 付き、スコア降順）
  state/candidates_top.json  … 上位 TOP_N（要約用、本文抜粋付き）
"""
import json
import os
import math
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state")

# --- 設定 ---
TOP_N = 25  # AI選抜に渡す候補プール（この中から AI が10本を選ぶ）
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
        c["score_detail"] = {
            "tag": round(tag_score, 2),
            "title": round(title_score, 2),
            "recency": round(rec, 2),
            "like": round(like, 2),
        }

    cands.sort(key=lambda c: c["score"], reverse=True)
    for i, c in enumerate(cands):
        c["rank"] = i + 1
        c["summarize"] = i < TOP_N

    with open(os.path.join(STATE, "candidates.json"), "w", encoding="utf-8") as f:
        json.dump(cands, f, ensure_ascii=False, indent=2)

    top = [
        {
            "key": c["key"],
            "title": c["title"],
            "url": c["url"],
            "hashtags": c.get("hashtags") or [],
            "description": c.get("description", ""),
            "body_excerpt": (c.get("body_excerpt", "") or "")[:600],
        }
        for c in cands
        if c["summarize"]
    ]
    with open(os.path.join(STATE, "candidates_top.json"), "w", encoding="utf-8") as f:
        json.dump(top, f, ensure_ascii=False, indent=2)

    print(f"scored {len(cands)} articles; top {len(top)} flagged for summary")
    for c in cands[:8]:
        print(f"  #{c['rank']:>2} {c['score']:>6}  {(c['title'] or '')[:38]:38}  {c.get('hashtags', [])[:4]}")


if __name__ == "__main__":
    main()
