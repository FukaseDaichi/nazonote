#!/bin/zsh
# 謎解き note 収集 — 日次オーケストレータ（launchd から呼ばれる）
# 手動テスト: zsh scripts/run.sh
set -u

ROOT="/Users/fukasedaichi/git/note"
PY="/usr/bin/python3"
# launchd は最小 PATH なので明示する
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
cd "$ROOT" || exit 1
mkdir -p daily state

# 同梱 claude バイナリを最新バージョンから自動解決（パスにバージョン番号が入るため）
CB="$(printf '%s\n' "$HOME/Library/Application Support/Claude/claude-code"/*/claude.app/Contents/MacOS/claude 2>/dev/null | sort -V | tail -1)"
# headless 認証トークン（初回のみ `claude setup-token` で発行→ state/.claude_token に保存）
# 形式チェック: 正規トークン(sk-ant-...)のときだけ使う。プレースホルダ等の誤貼り付けは無視。
if [ -f "$ROOT/state/.claude_token" ]; then
  _tok="$(tr -d '[:space:]' < "$ROOT/state/.claude_token")"
  case "$_tok" in
    sk-ant-*) export CLAUDE_CODE_OAUTH_TOKEN="$_tok" ;;
    *) echo "[warn] state/.claude_token が正しい形式(sk-ant-...)でないため無視（要約はスキップ）" ;;
  esac
  unset _tok
fi

notify() {
  /usr/bin/osascript -e "display notification \"$1\" with title \"謎解きnote収集\" sound name \"Glass\"" 2>/dev/null
}

{
  echo "=== run $(date '+%Y-%m-%d %H:%M:%S') ==="

  "$PY" scripts/learn.py    || echo "[warn] learn.py failed (continue)"

  if ! "$PY" scripts/collect.py; then
    notify "⚠️ 収集失敗 (state/run.log を確認)"
    echo "[fatal] collect.py failed"; exit 1
  fi

  if ! "$PY" scripts/score.py; then
    notify "⚠️ スコアリング失敗"
    echo "[fatal] score.py failed"; exit 1
  fi

  # 要約（claude バイナリがあれば試行）。未ログイン/失敗時は summaries.json が
  # 作られないだけで、render は note 原文の概要で問題なく続行する（耐障害）。
  if [ -n "$CB" ]; then
    rm -f state/summaries.json
    if ! "$CB" -p "$(cat prompts/summarize.md)" \
          --model sonnet \
          --permission-mode acceptEdits \
          --allowedTools Read,Write,Edit; then
      echo "[warn] claude summarize failed; rendering without summaries"
    fi
    [ -f state/summaries.json ] || echo "[info] no summaries.json (未ログイン等); 概要なしで描画"
  else
    echo "[info] claude binary not found; rendering without AI summaries"
  fi

  if ! "$PY" scripts/render.py; then
    notify "⚠️ レンダリング失敗"
    echo "[fatal] render.py failed"; exit 1
  fi

  MSG="$(cat state/notify.txt 2>/dev/null || echo '収集完了')"
  notify "$MSG"
  echo "=== done $(date '+%Y-%m-%d %H:%M:%S') ==="
} >> "$ROOT/state/run.log" 2>&1
