# データ契約

## ディレクトリ

- `daily/`: ユーザーが読む成果物と、checkbox によるフィードバック面
- `state/`: 永続状態、中間生成物、ログ、通知文
- `.claude/skills/nazo-digest/`: AI の評価・選抜・執筆仕様

## 永続状態

### `state/weights_base.json`

手動調整する基本タグ重みです。key はタグまたはタイトル部分一致に使う語、value はスコア加点・減点です。

```json
{
  "考察": 5,
  "一枚謎": 5,
  "感想": -4
}
```

利用箇所は `scripts/score.py` です。タグ完全一致の合計と、タイトルに key が含まれる場合の部分一致加点に使われます。

### `state/weights_learned.json`

`scripts/learn.py` が `state/feedback.jsonl` から毎回再構築する学習済みタグ重みです。

```json
{
  "一枚謎": 3.0,
  "水平思考クイズ": 2.0
}
```

`LEARN_STEP` は 1.0、タグごとの上限 `CAP` は 10.0 です。

### `state/feedback.jsonl`

ユーザーが過去の日次 Markdown で `- [x]` にした記事の履歴です。1 行 1 JSON です。

```json
{"key":"nb6119186abc7","tags":["水平思考クイズ","ウミガメのスープ"],"date":"2026-06-01"}
```

key 単位で重複排除されます。同じ記事を `daily/YYYY-MM-DD.md` と `daily/YYYY-MM-DD-osusume.md` の両方でチェックしても二重加算されません。

### `state/seen.json`

既出記事 key のリストです。`collect.py` が収集時に除外し、`render.py` が処理完了時に追記します。

```json
[
  "nb6119186abc7",
  "n5de0d68e52c9"
]
```

## 中間生成物

### `state/candidates_raw.json`

`collect.py` の出力です。note 検索 API と詳細 API から取得した生候補です。

```json
[
  {
    "key": "n5de0d68e52c9",
    "title": "【英語あそび211】判じ絵",
    "user": "wannatak",
    "publish_at": "2026-06-01T06:11:00.000+09:00",
    "like_count": 0,
    "comment_count": 0,
    "query": "謎解き",
    "hashtags": ["英語", "英語パズル"],
    "url": "https://note.com/wannatak/n/n5de0d68e52c9",
    "description": "",
    "body_excerpt": "本文冒頭..."
  }
]
```

### `state/candidates.json`

`score.py` の全件出力です。`candidates_raw.json` に機械スコア、順位、AI プール対象フラグが追加されます。

```json
[
  {
    "key": "n5de0d68e52c9",
    "title": "【英語あそび211】判じ絵",
    "url": "https://note.com/wannatak/n/n5de0d68e52c9",
    "hashtags": ["英語", "英語パズル"],
    "score": 2.5,
    "rank": 1,
    "pool": true
  }
]
```

### `state/candidates_top.json`

AI に渡す候補プールです。`POOL_N` は 40 件です。本文抜粋は 500 文字に短縮されます。

```json
[
  {
    "key": "n5de0d68e52c9",
    "title": "【英語あそび211】判じ絵",
    "url": "https://note.com/wannatak/n/n5de0d68e52c9",
    "user": "wannatak",
    "like_count": 0,
    "publish_at": "2026-06-01T06:11:00.000+09:00",
    "hashtags": ["英語", "英語パズル"],
    "description": "",
    "body_excerpt": "本文冒頭...",
    "mech_score": 2.5,
    "meta": "@wannatak · like0 · 2026-06-01T06:11 · #英語 #英語パズル",
    "marker": "<!-- key=n5de0d68e52c9 tags=英語,英語パズル -->"
  }
]
```

実コードの `meta` にはハート記号が使われます。`marker` は学習用なので、AI と Markdown 出力で改変してはいけません。

### `state/assessments.json`

AI の全候補評価です。

```json
{
  "assessed": [
    {
      "key": "n5de0d68e52c9",
      "ai_score": 70,
      "genre": "一枚謎",
      "gist": "英語の判じ絵パズル"
    }
  ]
}
```

`genre` はスキル定義上、`考察`、`一枚謎`、`制作`、`解説`、`推理小説`、`脱出公演`、`感想・レポ`、`宣伝・告知`、`無関係` のいずれかです。

### `state/selection.json`

AI のおすすめ選抜結果です。

```json
{
  "intro": "今日はその場で解ける記事が多め...",
  "picks": [
    {
      "rank": 1,
      "key": "n5de0d68e52c9",
      "blurb": "英語の判じ絵パズル...",
      "reason": "英語とひらめきが好きな人に"
    }
  ]
}
```

`render.py` は `picks` が存在する場合、全件チェックリストに `★N位` を付けます。存在しない場合は機械スコア上位 10 件を暫定おすすめ扱いにします。

### `state/today.txt`

対象日付を `YYYY-MM-DD` 形式で保持します。`score.py` が JST 現在日で書き、AI と `render.py` が出力ファイル名に使います。

### `state/notify.txt`

通知本文です。例:

```text
本日 27件 / おすすめ1位: 難易度:★★★★☆｜記録No.034...
```

現状は Mac 通知にだけ使われます。携帯通知対応では、この文面に当日ダイジェスト URL を組み合わせます。

## 成果物 Markdown

### `daily/YYYY-MM-DD.md`

全候補のチェックリストです。各行には学習用 marker が含まれます。

```markdown
- [ ] [記事タイトル](https://note.com/user/n/key) · AI70(一枚謎) ★1位 · #タグ <!-- key=n5de0d68e52c9 tags=英語,英語パズル -->
```

ユーザーが `- [ ]` を `- [x]` に変更すると、次回 `learn.py` が key と tags を抽出します。

### `daily/YYYY-MM-DD-osusume.md`

読むためのダイジェストです。各おすすめ記事にも学習用 checkbox 行があります。

```markdown
## 1位 [記事タイトル](https://note.com/user/n/key)
紹介文
おすすめ理由
`@user · like0 · 2026-06-01T06:11 · #タグ`
- [ ] 気になる <!-- key=n5de0d68e52c9 tags=英語,英語パズル -->
```

## Git 管理方針

`.gitignore` では、トークン、env、ローカル個人設定、ログ、中間 JSON、学習状態、全件チェックリストを除外しています。

追跡対象として残す想定のデータは次です。

- `state/weights_base.json`
- `daily/*-osusume.md`

Phase 1 の携帯閲覧では、最終的に public になる GitHub repository へ `daily/YYYY-MM-DD-osusume.md` だけを push します。`daily/YYYY-MM-DD.md`、`state/weights_learned.json`、`state/seen.json`、`state/feedback.jsonl` はローカル運用・学習用として Git の追跡対象から外します。
