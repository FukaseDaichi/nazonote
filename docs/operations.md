# 運用設計

## 初回セットアップ

1. Claude Code の headless 用トークンを発行します。
2. `state/.claude_token` に保存し、権限を `600` にします。
3. `zsh /Users/fukasedaichi/git/note/scripts/run.sh` で手動実行します。
4. `daily/YYYY-MM-DD-osusume.md` が暫定版ではなく AI 執筆版になっていることを確認します。
5. launchd に `com.fukase.nazo-daily.plist` を登録します。

`state/.claude_token` は `.gitignore` で除外されています。コミットしてはいけません。

## 日次運用

1. 08:00 に launchd が `scripts/run.sh` を起動します。
2. 実行ログは `state/run.log` に追記されます。
3. 完了すると Mac 通知センターに `state/notify.txt` の内容が通知されます。
4. ユーザーは `daily/YYYY-MM-DD-osusume.md` を読みます。
5. 気になる記事の checkbox を `- [x]` にします。
6. 翌日以降、`learn.py` がチェック済み記事のタグを学習します。

## 手動実行

```sh
zsh /Users/fukasedaichi/git/note/scripts/run.sh
```

ログ確認:

```sh
tail -f /Users/fukasedaichi/git/note/state/run.log
```

launchd の即時実行:

```sh
launchctl kickstart gui/$(id -u)/com.fukase.nazo-daily
```

launchd の停止:

```sh
launchctl bootout gui/$(id -u)/com.fukase.nazo-daily
```

## 失敗時の挙動

| 失敗箇所 | 現行挙動 | 確認先 |
| --- | --- | --- |
| `learn.py` | 警告を出して続行 | `state/run.log` |
| `collect.py` | fatal。通知して終了 | `state/run.log`, `state/launchd.err.log` |
| `score.py` | fatal。通知して終了 | `state/run.log` |
| AI 呼び出し | 警告を出して続行。`render.py` が暫定版を生成 | `state/run.log`, `daily/*-osusume.md` |
| `render.py` | fatal。通知して終了 | `state/run.log` |
| Mac 通知 | `osascript` エラーは捨てる | 通知が来なければ `state/run.log` |

## 再実行時の注意

同じ日に `run.sh` を再実行すると、当日の `daily/YYYY-MM-DD.md` は再生成されます。その日の checkbox 変更は、次回 `learn.py` が読む前に上書きされる可能性があります。

同日再収集では `state/seen.json` により既出記事が除外されます。全候補を再収集したい場合は、`seen.json` の扱いを手動で調整する必要があります。

## セキュリティ

- `state/.claude_token` はローカル秘密情報です。
- 今後 LINE Messaging API、GitHub URL などを足す場合は `state/.env` に置き、git 管理から除外します。
- note 記事本文の抜粋や AI 要約は `daily/` に残ります。Phase 1 では public GitHub に `daily/*-osusume.md` だけを push し、全件チェックリストと学習 state はローカル専用にします。

## 保守ポイント

- 収集クエリは `scripts/collect.py` の `QUERIES` で調整します。
- 収集対象時間は `WINDOW_HOURS` で調整します。
- AI 候補プール件数は `scripts/score.py` の `POOL_N` で調整します。
- 事前重みは `state/weights_base.json` で調整します。
- AI 評価基準と文体は `.claude/skills/nazo-digest/SKILL.md` で調整します。
- 学習をリセットする場合は `state/feedback.jsonl` と `state/weights_learned.json` の扱いを決めてから行います。

## 監視観点

- `state/run.log` に `fatal` が出ていないか
- `daily/YYYY-MM-DD-osusume.md` が `AI未実行の暫定版` になっていないか
- `state/candidates_raw.json` の件数が急に 0 になっていないか
- `state/seen.json` が肥大化しすぎていないか
- note API のレスポンス形式変更で `hashtags`、`description`、`body` が空になっていないか
