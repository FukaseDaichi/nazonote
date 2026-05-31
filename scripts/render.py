#!/usr/bin/env python3
"""candidates.json (+ あれば summaries.json) から日次 Markdown を生成する。

- daily/YYYY-MM-DD.md を出力
- 各記事行に隠しマーカー <!-- key=... tags=... --> を埋め込む（学習用）
- 出力した key を seen.json に追記（重複防止）
- 通知用の1行を state/notify.txt に書く
summaries.json が無い/壊れていても、note原文の概要で問題なく動く（耐障害）。
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


def tags_inline(c):
    return " ".join("#" + t for t in (c.get("hashtags") or [])[:6])


def tags_marker(c):
    return ",".join(c.get("hashtags") or [])


def main():
    cands = load(os.path.join(STATE, "candidates.json"), [])
    summ = load(os.path.join(STATE, "summaries.json"), {}) or {}
    arts = summ.get("articles") or {}
    today = datetime.datetime.now(JST).strftime("%Y-%m-%d")

    top = [c for c in cands if c.get("summarize")]
    rest = [c for c in cands if not c.get("summarize")]

    L = []
    L.append(f"# 謎解き note 収集 — {today}\n")
    L.append(f"収集 **{len(cands)}** 件（注目 {len(top)} 件＋その他 {len(rest)} 件）\n")

    if summ.get("daily_summary"):
        L.append("## 本日のまとめ\n")
        L.append(summ["daily_summary"] + "\n")

    pick = summ.get("pick") or {}
    if pick.get("key"):
        pc = next((c for c in cands if c["key"] == pick["key"]), None)
        if pc:
            L.append("## まず読む1本\n")
            L.append(f"**[{pc['title']}]({pc['url']})** — {pick.get('reason', '')}\n")

    L.append("## 注目記事\n")
    for c in top:
        L.append(f"### #{c['rank']} [{c['title']}]({c['url']})　·　score {c['score']}")
        meta = f"@{c.get('user', '')} · ❤ {c.get('like_count', 0)} · {(c.get('publish_at') or '')[:16]}"
        ti = tags_inline(c)
        if ti:
            meta += f" · {ti}"
        L.append(meta)
        a = arts.get(c["key"])
        if a:
            if a.get("overview"):
                L.append(f"\n**概要**: {a['overview']}")
            for p in (a.get("points") or []):
                L.append(f"- {p}")
        elif c.get("description"):
            L.append(f"\n**概要(note原文)**: {c['description']}")
        L.append(f"\n- [ ] 気になる <!-- key={c['key']} tags={tags_marker(c)} -->\n")

    if rest:
        L.append("## その他\n")
        for c in rest:
            ti = tags_inline(c)
            suffix = (" · " + ti) if ti else ""
            L.append(
                f"- [ ] [{c['title']}]({c['url']}) · score {c['score']}{suffix} "
                f"<!-- key={c['key']} tags={tags_marker(c)} -->"
            )
        L.append("")

    os.makedirs(DAILY, exist_ok=True)
    out = os.path.join(DAILY, f"{today}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # seen.json 更新
    seenp = os.path.join(STATE, "seen.json")
    seen = set(load(seenp, []))
    for c in cands:
        seen.add(c["key"])
    with open(seenp, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=0)

    # 通知文
    notable = (top[0]["title"] if top else (cands[0]["title"] if cands else "なし"))[:30]
    with open(os.path.join(STATE, "notify.txt"), "w", encoding="utf-8") as f:
        f.write(f"本日 {len(cands)}件 / 注目: {notable}")

    print(f"wrote {out} ({len(cands)} articles, {len(arts)} summarized)")


if __name__ == "__main__":
    main()
