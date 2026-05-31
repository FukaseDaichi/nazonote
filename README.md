# 謎解き note 自動収集システム

毎日「謎解き」関連の note 記事を自動収集し、2つの Markdown を生成する。

- `daily/YYYY-MM-DD-osusume.md` … **AI選抜「おすすめTOP10」記事**（読む用）。各記事の「どんな記事か」＋おすすめ理由つき。
- `daily/YYYY-MM-DD.md` … 全件のスコア順チェックリスト（学習用フィードバック面）。

気になった記事の `- [ ]` を `- [x]` にすると、そのタグ傾向（考察・一枚謎など）を学習して翌日以降の順位に反映する。すべてローカル Mac・無料・個人利用想定。

## 仕組み

```
launchd(毎日8:00) → run.sh
  1. learn.py    過去mdの [x] を集計 → state/weights_learned.json
  2. collect.py  note API(検索+詳細) → 直近28hの新着 → state/candidates_raw.json
  3. score.py    base+learned 重みで採点 → 上位25件を候補プールに → state/candidates*.json
  4. claude -p   プール25件から AI が10本を選抜・要約 → state/summaries.json
  5. render.py   osusume.md（TOP10記事）と 全件.md を生成
  6. 通知        osascript で macOS 通知
```

依存は **Python 標準ライブラリのみ**（pip 不要）。データ取得は note の公開 JSON API。
トークン未設定でも 1〜3,5,6 は動き、TOP10 は**スコア順の暫定版**で出る（AI選抜のみ要トークン）。

## セットアップ（初回1回だけ）— AI選抜を有効化

要約・選抜に Claude を使うため、自動化用の長期トークンを発行する（あなたのサブスクで無料）。

```sh
# 1) トークン発行（ブラウザ認証が開く。表示される sk-ant-... をコピー）
CLAUDE="$(ls -t "$HOME/Library/Application Support/Claude/claude-code/"*/claude.app/Contents/MacOS/claude | head -1)"
"$CLAUDE" setup-token

# 2) コピーした値を保存（★下の行の sk-ant-... を、実際にコピーしたトークンに置き換える）
TOKEN='sk-ant-ここに貼り付け'
printf '%s' "$TOKEN" > ~/git/note/state/.claude_token
chmod 600 ~/git/note/state/.claude_token

# 3) 形式チェック（"OK" が出れば正しく貼れている）
case "$(cat ~/git/note/state/.claude_token)" in sk-ant-*) echo OK;; *) echo "NG: 置き換え忘れ";; esac

# 4) 本番テスト（osusume.md の見出しが「AI が…選抜」になれば成功）
zsh ~/git/note/scripts/run.sh && tail -20 ~/git/note/state/run.log
```

> 注意: 手順2で `sk-ant-ここに貼り付け` をそのまま実行しないこと。実際のトークンに置き換える。
> 形式が `sk-ant-` でないトークンは run.sh が自動で無視し、暫定版（スコア順）で描画する。

## 日々の使い方

1. 朝、通知が来たら `daily/YYYY-MM-DD-osusume.md`（AI選抜TOP10）を開いて読む。
2. 気になった記事の `- [ ]` を **`- [x]`** に変えて保存（osusume / 全件どちらのmdでも可）。
3. 翌日以降、その系統（考察・一枚謎など）が上位に来やすくなる。

## 優先度の調整

`state/weights_base.json` を手で編集（タグ名→重み）。プラスで優先、マイナスで抑制。
スコアは AI選抜前の「候補プール25件」を決めるのに使われる（最終10本はAIが選ぶ）。

- 既定で優先: 考察(+5) 一枚謎(+5) 謎解き制作(+4) 自作謎(+4) 解説(+3) 暗号(+3) …
- 既定で抑制: 感想(-4) 参加レポ(-4) 行ってきた(-4) 参加(-3) レポ(-3) イベント(-2) …

学習加点は `state/weights_learned.json`（自動・`feedback.jsonl` から毎回再構築）。
リセットは `feedback.jsonl` を空にして `weights_learned.json` を削除。

## 手動実行・管理

```sh
zsh ~/git/note/scripts/run.sh          # 手動で1回実行
tail -f ~/git/note/state/run.log       # 実行ログ

launchctl list | grep nazo             # 登録確認
launchctl kickstart gui/$(id -u)/com.fukase.nazo-daily   # 即時実行
launchctl bootout gui/$(id -u)/com.fukase.nazo-daily     # 停止/解除
```

## 注意

- **同じ日に run.sh を2回流すと当日 md は作り直される**（その日の [x] は消える）。
  チェックは翌朝の実行前までに付ければ学習される（翌日以降は過去日 md として読まれる）。
- 同日2回目以降は seen.json により**新着のみ**収集する（前回分は重複除外）。1日まとめて見たい運用ならこれが正しい挙動。
- 収集クエリ・件数・時間窓は `scripts/collect.py` 冒頭、採点の重みは `scripts/score.py` 冒頭で調整。
- note の API は非公式のため仕様変更の可能性あり。失敗時は通知が出る。
- 礼儀として詳細取得に 0.4s スリープ・1日1回・個人利用に限定。
- `daily/*.md` は生成物。git で追跡したくなければ `.gitignore` に `daily/*.md` を追加してよい（学習は `feedback.jsonl` に残るので影響なし）。

## ファイル構成

```
scripts/{collect,score,learn,render}.py  パイプライン各段
scripts/run.sh                            オーケストレータ（launchd が実行）
prompts/summarize.md                      claude -p への選抜・要約指示
state/weights_base.json                   基本重み（手調整可）
state/weights_learned.json                学習重み（自動）
state/seen.json                           既出キー（重複防止）
state/feedback.jsonl                      [x] 履歴
state/.claude_token                       認証トークン（gitignore・600）
daily/YYYY-MM-DD-osusume.md               AI選抜おすすめTOP10（読む用）
daily/YYYY-MM-DD.md                       全件チェックリスト（学習用）
com.fukase.nazo-daily.plist               launchd 定義
```
