# 謎解き note 自動収集システム

毎日「謎解き」関連の note 記事を収集し、**AIが全候補を評価・採点 → おすすめを選抜 → フランクな語り口でダイジェスト記事を執筆**する。出力は2つの Markdown：

- `daily/YYYY-MM-DD-osusume.md` … 「こんなのあったよ！」と紹介する **AI執筆のおすすめダイジェスト**（読む用）。
- `daily/YYYY-MM-DD.md` … 全件チェックリスト（AIスコア併記・学習用フィードバック面）。

気になった記事の `- [ ]` を `- [x]` にすると、そのタグ傾向を学習し、翌日のAI選抜に「好み」として渡す。すべてローカル Mac・無料・個人利用想定。

## 全体構成（AIを全段に）

```
launchd(毎日8:00) → run.sh
  1. learn.py     [機械] 過去[x]を集計 → weights_learned.json（AIへ渡す“好み”）
  2. collect.py   [機械] note API → 全候補(本文/タグ/概要) → candidates_raw.json
  3. score.py     [機械] 下ごしらえ並べ替え＋候補プール40件 → candidates_top.json / today.txt
  ── ここから判断・執筆は全部AI（スキル nazo-digest）──
  4. /nazo-digest [AI]  A. 全候補を内容確認しAIスコア+ジャンル+一言 → assessments.json
                        B. その上でおすすめTOP10を選抜          → selection.json
                        C. フランクに記事を執筆                  → daily/DATE-osusume.md
  5. render.py    [機械] 全件チェックリスト生成（AIスコア併記）。AI未実行なら暫定ダイジェストで代替
  6. 通知         [機械] osascript
```

機械処理は「取得・並べ替え・整形・通知」の配管だけ。**採点・選抜・執筆はすべて AI**。
依存は Python 標準ライブラリのみ（pip 不要）。データ取得は note の公開 JSON API。

## スキル `nazo-digest`

記事の評価・選抜・執筆は `.claude/skills/nazo-digest/SKILL.md`（リポジトリスキル）に実装。

- 手動: Claude Code で **`/nazo-digest`** と打てばその場で本日のダイジェストを作る。
- 自動: `run.sh` が `claude -p "/nazo-digest"` で起動（headlessでスラッシュが効かない場合はスキル本文を直接渡す保険つき）。

トークン未設定でも 1〜3,5,6 は動き、ダイジェストは **スコア順の暫定版** が出る（AI評価・選抜・フランク執筆のみ要トークン）。

## セットアップ（初回1回だけ）— AIを有効化

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

# 4) 本番テスト（osusume.md の冒頭が「⚠️ AI未実行」でなくフランクな本文になれば成功）
zsh ~/git/note/scripts/run.sh && tail -25 ~/git/note/state/run.log
```

> 手順2の `sk-ant-ここに貼り付け` をそのまま実行しないこと。形式が `sk-ant-` でない値は run.sh が自動で無視し、暫定版で描画する。

## 日々の使い方

1. 朝、通知が来たら `daily/YYYY-MM-DD-osusume.md`（AIダイジェスト）を読む。
2. 気になった記事の `- [ ]` を **`- [x]`** に（osusume / 全件どちらのmdでも可）。
3. 翌日以降、その系統が AI のおすすめに反映されやすくなる。

## 調整

- 機械の事前重み: `state/weights_base.json`（タグ→重み。候補プールの質に効く）。
- 候補プール件数・クエリ・時間窓: `scripts/collect.py` / `scripts/score.py` 冒頭。
- 評価基準・選抜方針・記事のトーン: `.claude/skills/nazo-digest/SKILL.md` を編集。
- 学習: `state/weights_learned.json`（自動・`feedback.jsonl` から再構築）。リセットは両者を消す。

## 手動実行・管理

```sh
zsh ~/git/note/scripts/run.sh          # 手動で1回（収集→AI→描画→通知）
tail -f ~/git/note/state/run.log       # ログ
/nazo-digest                           # Claude Code 内で、収集済み候補から記事だけ作り直す

launchctl list | grep nazo                                # 登録確認
launchctl kickstart gui/$(id -u)/com.fukase.nazo-daily    # 即時実行
launchctl bootout  gui/$(id -u)/com.fukase.nazo-daily     # 停止/解除
```

## 注意

- **同じ日に run.sh を2回流すと当日 md は作り直される**（その日の [x] は消える）。チェックは翌朝の実行前までに。
- 同日2回目以降は seen.json により**新着のみ**収集（前回分は重複除外）。フル収集し直すなら `echo '[]' > state/seen.json`。
- note API は非公式のため仕様変更の可能性あり。失敗時は通知が出る。礼儀として詳細取得0.4sスリープ・1日1回・個人利用に限定。
- `daily/*.md` は生成物。git追跡したくなければ `.gitignore` に `daily/*.md` を追加してよい（学習は feedback.jsonl に残る）。
- スキルを git に含めるには `git add .claude/skills/`（`.claude/settings.local.json` は個人設定なので通常コミットしない）。

## ファイル構成

```
scripts/{collect,score,learn,render}.py   収集・下ごしらえ・学習・整形(配管)
scripts/run.sh                             オーケストレータ（launchd が実行）
.claude/skills/nazo-digest/SKILL.md        ★AIの評価・選抜・フランク執筆スキル
state/weights_base.json / weights_learned.json   重み（手調整 / 学習）
state/candidates*.json / today.txt          中間データ
state/assessments.json / selection.json     AIの採点 / 選抜結果
state/seen.json / feedback.jsonl            重複防止 / [x]履歴
state/.claude_token                         認証トークン（gitignore・600）
daily/YYYY-MM-DD-osusume.md                 AIダイジェスト（読む用）
daily/YYYY-MM-DD.md                         全件チェックリスト（学習用）
com.fukase.nazo-daily.plist                 launchd 定義
```
