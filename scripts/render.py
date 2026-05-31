#!/usr/bin/env python3
"""candidates.json (+ あれば summaries.json) から2つの Markdown を生成する。

1) daily/YYYY-MM-DD-osusume.md … AI選抜「おすすめ謎解き TOP10」記事（読む用）
2) daily/YYYY-MM-DD.md          … 全件のスコア順チェックリスト（学習用フィードバック面）

両方の各記事行に隠しマーカー <!-- key=... tags=... --> を埋める（learn.py が拾う）。
summaries.json が無い/壊れている場合は、TOP10 を **スコア順** で暫定生成する（耐障害）。
"""
import json
import os
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state")
DAILY = os.path.join(ROOT, "daily")
JST = datetime.timezone(datetime.timedelta(hours=9))


def load(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def tags_inline(c, n=6):
    return " ".join("#" + t for t in (c.get("hashtags") or [])[:n])


def tags_marker(c):
    return ",".join(c.get("hashtags") or [])


def meta_line(c):
    s = f"@{c.get('user', '')} · ❤{c.get('like_count', 0)} · {(c.get('publish_at') or '')[:16]}"
    ti = tags_inline(c)
    return s + (f" · {ti}" if ti else "")


def main():
    cands = load(os.path.join(STATE, "candidates.json"), [])
    summ = load(os.path.join(STATE, "summaries.json"), {}) or {}
    by_key = {c["key"]: c for c in cands}
    today = datetime.datetime.now(JST).strftime("%Y-%m-%d")

    lead = summ.get("lead") or summ.get("daily_summary") or ""
    ranking = summ.get("ranking") or []
    ai_picked = bool(ranking)

    # フォールバック: AI選抜が無ければスコア上位10件で暫定ランキング
    if not ai_picked:
        ranking = [
            {
                "rank": i + 1,
                "key": c["key"],
                "description": c.get("description", ""),
                "reason": "",
            }
            for i, c in enumerate(cands[:10])
        ]

    picked = {}  # key -> rank（コレクション md の ★バッジ用）

    # ---------- 1) おすすめ TOP10 記事 ----------
    A = []
    A.append(f"# 🧩 今日のおすすめ謎解き note TOP10 — {today}\n")
    if lead:
        A.append(lead + "\n")
    if ai_picked:
        A.append("> AI が本日の候補から選抜・要約。気になった記事は `- [ ]` を `- [x]` に。\n")
    else:
        A.append("> ⚠️ AI未選抜（スコア順の暫定版）。`claude setup-token` 後に本選抜が有効になります。\n")

    for item in ranking:
        key = item.get("key")
        c = by_key.get(key)
        if not c:
            continue
        rank = item.get("rank", "?")
        picked[key] = rank
        A.append(f"## {rank}位　[{c['title']}]({c['url']})")
        desc = (item.get("description") or "").strip()
        if desc:
            A.append(f"\n{desc}")
        reason = (item.get("reason") or "").strip()
        if reason:
            A.append(f"\n**おすすめ理由**: {reason}")
        A.append(f"\n`{meta_line(c)}`")
        A.append(f"\n- [ ] 気になる <!-- key={key} tags={tags_marker(c)} -->\n")

    os.makedirs(DAILY, exist_ok=True)
    osusume_path = os.path.join(DAILY, f"{today}-osusume.md")
    with open(osusume_path, "w", encoding="utf-8") as f:
        f.write("\n".join(A) + "\n")

    # ---------- 2) 全件チェックリスト ----------
    L = []
    L.append(f"# 謎解き note 収集（全{len(cands)}件） — {today}\n")
    if lead:
        L.append("## 本日のまとめ\n")
        L.append(lead + "\n")
    L.append(f"→ AI選抜おすすめTOP10: [{today}-osusume.md]({today}-osusume.md)\n")
    L.append("## 一覧（スコア順・気になるものを [x] に）\n")
    for c in cands:
        badge = f" ★AI{picked[c['key']]}位" if c["key"] in picked else ""
        ti = tags_inline(c, 5)
        suffix = (" · " + ti) if ti else ""
        L.append(
            f"- [ ] [{c['title']}]({c['url']}) · score {c['score']}{badge}{suffix} "
            f"<!-- key={c['key']} tags={tags_marker(c)} -->"
        )
    L.append("")
    collection_path = os.path.join(DAILY, f"{today}.md")
    with open(collection_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # ---------- seen.json 更新 ----------
    seenp = os.path.join(STATE, "seen.json")
    seen = set(load(seenp, []))
    for c in cands:
        seen.add(c["key"])
    with open(seenp, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=0)

    # ---------- 通知文 ----------
    top1 = next((by_key[i["key"]]["title"] for i in ranking if i.get("key") in by_key), "なし")
    tag = "おすすめ1位" if ai_picked else "暫定1位"
    with open(os.path.join(STATE, "notify.txt"), "w", encoding="utf-8") as f:
        f.write(f"本日 {len(cands)}件 / {tag}: {top1[:28]}")

    print(
        f"wrote {os.path.basename(osusume_path)} (TOP{len(picked)}, "
        f"{'AI選抜' if ai_picked else 'スコア順'}) + {os.path.basename(collection_path)} ({len(cands)}件)"
    )


if __name__ == "__main__":
    main()
