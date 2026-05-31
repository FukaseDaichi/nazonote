#!/usr/bin/env python3
"""過去の日次 md でチェックされた記事から、学習重みを更新する。

- daily/*.md（直近 LOOKBACK_DAYS 日）を走査し、`- [x] ... <!-- key=K tags=T -->` を抽出
- 新規チェック分のみ feedback.jsonl に追記（key で重複排除）
- feedback.jsonl 全体から weights_learned.json を毎回再構築（冪等：二重加算しない）

ユーザーは気になった記事の `- [ ]` を `- [x]` に変えて保存するだけでよい。
"""
import json
import os
import re
import glob
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state")
DAILY = os.path.join(ROOT, "daily")

LEARN_STEP = 1.0     # チェック1回ごとの加点
CAP = 10.0           # 1タグの学習重み上限
LOOKBACK_DAYS = 60   # 走査する日次mdの遡り日数

CHECK_RE = re.compile(r"\[x\].*?<!--\s*key=(\S+)\s+tags=([^>]*?)\s*-->")


def main():
    os.makedirs(STATE, exist_ok=True)
    fb = os.path.join(STATE, "feedback.jsonl")

    known = set()
    if os.path.exists(fb):
        for line in open(fb, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                known.add(json.loads(line)["key"])
            except Exception:
                pass

    today = datetime.date.today()
    new = []
    for md in sorted(glob.glob(os.path.join(DAILY, "*.md"))):
        base = os.path.basename(md)[:10]  # 先頭の YYYY-MM-DD（-osusume.md も拾う）
        try:
            d = datetime.date.fromisoformat(base)
            if (today - d).days > LOOKBACK_DAYS:
                continue
        except Exception:
            pass
        text = open(md, encoding="utf-8").read()
        for m in CHECK_RE.finditer(text):
            key = m.group(1)
            tags = [t for t in m.group(2).split(",") if t]
            if key in known:
                continue
            known.add(key)
            new.append({"key": key, "tags": tags, "date": base})

    if new:
        with open(fb, "a", encoding="utf-8") as f:
            for e in new:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # feedback.jsonl 全体から学習重みを再構築（冪等）
    weights = {}
    if os.path.exists(fb):
        for line in open(fb, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            for t in e.get("tags", []):
                weights[t] = min(CAP, weights.get(t, 0) + LEARN_STEP)

    with open(os.path.join(STATE, "weights_learned.json"), "w", encoding="utf-8") as f:
        json.dump(weights, f, ensure_ascii=False, indent=2)

    print(f"learn: +{len(new)} new checked article(s); learned tags={len(weights)}")


if __name__ == "__main__":
    main()
