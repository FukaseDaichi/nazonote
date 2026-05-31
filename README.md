# 謎解き note 自動収集システム

毎日「謎解き」関連の note 記事を自動収集し、優先度順に 1 枚の Markdown へまとめる。
気になった記事に `[x]` を付けると、その傾向（タグ）を学習して翌日以降の順位に反映する。
すべてローカル Mac・無料・個人利用想定。

## 仕組み

```
launchd(毎日8:00) → run.sh
  1. learn.py    過去mdの [x] を集計 → state/weights_learned.json
  2. collect.py  note API(検索+詳細) → 直近28hの記事 → state/candidates_raw.json
  3. score.py    base+learned 重みで採点・並べ替え → state/candidates.json
  4. claude -p   上位15件を要約 → state/summaries.json（トークン設定後に有効）
  5. render.py   daily/YYYY-MM-DD.md を生成
  6. 通知        osascript で macOS 通知
```

依存は **Python 標準ライブラリのみ**（pip 不要）。データ取得は note の公開 JSON API。

## セットアップ（初回1回だけ）— AI要約を有効化

要約に Claude を使うため、自動化用の長期トークンを発行する（あなたのサブスクで無料）。

```sh
# 1) 同梱 claude を起動してトークン発行（ブラウザ認証が開く）
CLAUDE="$(ls -t "$HOME/Library/Application Support/Claude/claude-code/"*/claude.app/Contents/MacOS/claude | head -1)"
"$CLAUDE" setup-token
# → 表示されたトークン(sk-ant-... )をコピー

# 2) トークンを保存（600 権限）
printf '%s' '＜コピーしたトークン＞' > "$HOME/git/note/state/.claude_token"
chmod 600 "$HOME/git/note/state/.claude_token"

# 3) 動作テスト（daily md に「本日のまとめ」「まず読む1本」が付けば成功）
zsh "$HOME/git/note/scripts/run.sh" && cat "$HOME/git/note/state/run.log" | tail -20
```

> 要約なしでも動く：トークン未設定でも、収集・採点・通知・md生成は全部動く。
> その場合「概要」は note 原文の説明文が入る（AI生成のまとめ／まず読む1本は出ない）。

## 日々の使い方

1. 朝、通知が来たら `daily/YYYY-MM-DD.md` を開く（Obsidian でも標準エディタでも可）。
2. 気になった記事の `- [ ]` を **`- [x]`** に変えて保存するだけ。
3. 翌日以降、そのタグ系統（考察・一枚謎など）が上位に来やすくなる。

## 優先度の調整

`state/weights_base.json` を手で編集（タグ名→重み）。プラスで優先、マイナスで抑制。

- 既定で優先: 考察(+5) 一枚謎(+5) 謎解き制作(+4) 自作謎(+4) 解説(+3) 暗号(+3) …
- 既定で抑制: 感想(-4) 参加レポ(-4) 行ってきた(-4) 参加(-3) レポ(-3) イベント(-2) …

学習による加点は `state/weights_learned.json`（自動生成・`feedback.jsonl` から毎回再構築）。
学習をリセットしたいときは両ファイルを消すか `feedback.jsonl` を空にする。

## 手動実行・管理

```sh
zsh ~/git/note/scripts/run.sh          # 手動で1回実行
tail -f ~/git/note/state/run.log       # 実行ログ

launchctl list | grep nazo             # 登録確認
launchctl kickstart gui/$(id -u)/com.fukase.nazo-daily   # 即時実行
launchctl bootout gui/$(id -u)/com.fukase.nazo-daily     # 停止/解除
# 時刻変更などで plist を編集したら、bootout→再コピー→bootstrap で再読込
cp ~/git/note/com.fukase.nazo-daily.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.fukase.nazo-daily.plist
```

## 注意

- 同じ日に run.sh を2回流すと当日 md は作り直される（その日のチェックは消える）。
  チェックは翌朝の実行前までに付ければ学習される（翌日以降は過去日 md として読まれる）。
- 収集クエリ・件数・時間窓は `scripts/collect.py` 冒頭、採点の重みは `scripts/score.py` 冒頭で調整。
- note の API は非公式のため仕様変更の可能性あり。壊れたら `collect.py` を直す。失敗時は通知が出る。
- 礼儀として詳細取得に 0.4s スリープ・1日1回・個人利用に限定している。

## ファイル構成

```
scripts/{collect,score,learn,render}.py  パイプライン各段
scripts/run.sh                            オーケストレータ（launchd が実行）
prompts/summarize.md                      claude -p への要約指示
state/weights_base.json                   基本重み（手調整可）
state/weights_learned.json                学習重み（自動）
state/seen.json                           既出キー（重複防止）
state/feedback.jsonl                      [x] 履歴
state/.claude_token                       認証トークン（gitignore・600）
daily/YYYY-MM-DD.md                       日次成果物
com.fukase.nazo-daily.plist               launchd 定義
```
