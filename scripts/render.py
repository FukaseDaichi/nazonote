#!/usr/bin/env python3
"""機械的な配管: 全件チェックリストの生成と、AI(スキル)未実行時のフォールバック。

- daily/YYYY-MM-DD.md … 全件のチェックリスト（学習用フィードバック面）。
  AIの assessments があれば AIスコア/ジャンルを併記、selection があれば ★順位 を付ける。
- daily/YYYY-MM-DD-osusume.md … 通常はスキル nazo-digest が執筆済み。
  もし未作成（AI未実行/失敗）なら、ここでスコア順の **暫定ダイジェスト** を書く。

seen.json 更新と通知文の出力もここで行う。
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


def today_str():
    t = load(os.path.join(STATE, "today.txt"), None)
    if isinstance(t, str) and t.strip():
        return t.strip()
    try:
        return open(os.path.join(STATE, "today.txt"), encoding="utf-8").read().strip()
    except Exception:
        return datetime.datetime.now(JST).strftime("%Y-%m-%d")


def tags_inline(c, n=5):
    return " ".join("#" + t for t in (c.get("hashtags") or [])[:n])


def tags_marker(c):
    return ",".join(c.get("hashtags") or [])


def meta_line(c):
    s = f"@{c.get('user', '')} · ❤{c.get('like_count', 0)} · {(c.get('publish_at') or '')[:16]}"
    ti = tags_inline(c, 6)
    return s + (f" · {ti}" if ti else "")


def main():
    cands = load(os.path.join(STATE, "candidates.json"), [])
    by_key = {c["key"]: c for c in cands}
    today = today_str()

    assess = load(os.path.join(STATE, "assessments.json"), {}) or {}
    ai = {a["key"]: a for a in (assess.get("assessed") or []) if "key" in a}

    sel = load(os.path.join(STATE, "selection.json"), {}) or {}
    picks = sel.get("picks") or []
    intro = sel.get("intro") or ""

    # ★順位: AI選抜があればそれ、無ければスコア上位10件
    if picks:
        picked = {p["key"]: p.get("rank", "?") for p in picks if p.get("key")}
    else:
        picked = {c["key"]: i + 1 for i, c in enumerate(cands[:10])}

    # ---------- 全件チェックリスト ----------
    L = [f"# 謎解き note 収集（全{len(cands)}件） — {today}\n"]
    if intro:
        L.append("## 今日のひとこと（AI）\n")
        L.append(intro + "\n")
    L.append(f"→ おすすめダイジェスト: [{today}-osusume.md]({today}-osusume.md)\n")
    L.append("## 一覧（気になるものを [x] に）\n")
    for c in cands:
        a = ai.get(c["key"])
        if a:
            sc = f"AI{a.get('ai_score', '?')}({a.get('genre', '')})"
        else:
            sc = f"score{c.get('score', '?')}"
        badge = f" ★{picked[c['key']]}位" if c["key"] in picked else ""
        ti = tags_inline(c, 4)
        suffix = (" · " + ti) if ti else ""
        L.append(
            f"- [ ] [{c['title']}]({c['url']}) · {sc}{badge}{suffix} "
            f"<!-- key={c['key']} tags={tags_marker(c)} -->"
        )
    L.append("")
    os.makedirs(DAILY, exist_ok=True)
    with open(os.path.join(DAILY, f"{today}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    # ---------- おすすめ md（スキル未作成時のみ暫定生成） ----------
    osusume = os.path.join(DAILY, f"{today}-osusume.md")
    skill_wrote = os.path.exists(osusume) and bool(picks)
    if not skill_wrote:
        top = cands[:10]
        A = [f"# 🧩 今日の謎解きnote、こんなのあったよ！ — {today}\n"]
        A.append("> ⚠️ AI未実行の暫定版（スコア順）。`claude setup-token` と `/nazo-digest` で本番のAI選抜・執筆になります。\n")
        for i, c in enumerate(top):
            A.append(f"## {i + 1}位 [{c['title']}]({c['url']})")
            if c.get("description"):
                A.append(f"\n{c['description']}")
            A.append(f"\n`{meta_line(c)}`")
            A.append(f"\n- [ ] 気になる <!-- key={c['key']} tags={tags_marker(c)} -->\n")
        with open(osusume, "w", encoding="utf-8") as f:
            f.write("\n".join(A) + "\n")
        osusume_state = "暫定(スコア順)"
    else:
        osusume_state = "AI執筆済み"

    # ---------- seen.json ----------
    seenp = os.path.join(STATE, "seen.json")
    seen = set(load(seenp, []))
    for c in cands:
        seen.add(c["key"])
    with open(seenp, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=0)

    # ---------- 通知 ----------
    if picks:
        top1 = next((by_key[p["key"]]["title"] for p in picks if p.get("key") in by_key), "なし")
        tag = "おすすめ1位"
    else:
        top1 = cands[0]["title"] if cands else "なし"
        tag = "暫定1位"
    with open(os.path.join(STATE, "notify.txt"), "w", encoding="utf-8") as f:
        f.write(f"本日 {len(cands)}件 / {tag}: {top1[:26]}")

    print(f"render: 全件.md({len(cands)}件) + osusume.md[{osusume_state}] / AI評価 {len(ai)}件・選抜 {len(picks)}本")


if __name__ == "__main__":
    main()
