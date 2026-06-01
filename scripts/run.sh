#!/bin/zsh
# 謎解き note 収集 — 日次オーケストレータ（launchd から呼ばれる）
# 手動テスト: zsh scripts/run.sh
set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="/usr/bin/python3"
# launchd は最小 PATH なので明示する
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
cd "$ROOT" || exit 1
mkdir -p daily state

# 外部連携・通知設定。state/.env は gitignore 対象。
if [ -f "$ROOT/state/.env" ]; then
  set -a
  source "$ROOT/state/.env"
  set +a
fi

# 同梱 claude バイナリを最新バージョンから自動解決（パスにバージョン番号が入るため）
CB="$(printf '%s\n' "$HOME/Library/Application Support/Claude/claude-code"/*/claude.app/Contents/MacOS/claude 2>/dev/null | sort -V | tail -1)"
# headless 認証トークン（初回のみ `claude setup-token` で発行→ state/.claude_token に保存）
# 形式チェック: 正規トークン(sk-ant-...)のときだけ使う。プレースホルダ等の誤貼り付けは無視。
if [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && [ -f "$ROOT/state/.claude_token" ]; then
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

publish_digest() {
  local today osusume branch
  today="$(cat state/today.txt 2>/dev/null || date '+%Y-%m-%d')"
  osusume="daily/${today}-osusume.md"

  if [ ! -f "$osusume" ]; then
    echo "[warn] ${osusume} が無いため GitHub push / LINE 通知をスキップ"
    return 0
  fi
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[warn] git repository ではないため GitHub push / LINE 通知をスキップ"
    return 0
  fi

  git add -- "$osusume" || {
    echo "[warn] git add failed; GitHub push / LINE 通知をスキップ"
    return 0
  }
  if git diff --cached --quiet -- "$osusume"; then
    echo "[info] ${osusume} に差分なし; GitHub push / LINE 通知をスキップ"
    return 0
  fi

  if ! git commit -m "Add daily digest ${today}" -- "$osusume"; then
    echo "[warn] git commit failed; GitHub push / LINE 通知をスキップ"
    return 0
  fi

  branch="$(git branch --show-current 2>/dev/null)"
  if [ -z "$branch" ]; then
    echo "[warn] current branch 不明; GitHub push / LINE 通知をスキップ"
    return 0
  fi
  if git push origin "$branch"; then
    "$PY" scripts/line_notify.py || true
  else
    echo "[warn] git push failed; LINE 通知をスキップ"
  fi
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

  # AIダイジェスト: スキル nazo-digest が全候補を評価・選抜し、フランクな記事を執筆。
  # 未ログイン/失敗時は render.py が暫定版（スコア順）で代替するので止まらない（耐障害）。
  if [ -n "$CB" ]; then
    rm -f state/assessments.json state/selection.json
    # まずスラッシュ起動。これが headless で効かない環境では本文プロンプトに保険でフォールバック。
    "$CB" -p "/nazo-digest" --model sonnet --permission-mode acceptEdits \
        --allowedTools "Read,Write,Edit,Skill" || echo "[warn] /nazo-digest 呼び出しに失敗"
    if [ ! -f state/selection.json ]; then
      echo "[info] selection.json 未生成 → スキル本文を直接プロンプトで再試行"
      BODY="$(awk 'c>=2{print} /^---[ \t]*$/{c++}' .claude/skills/nazo-digest/SKILL.md)"
      "$CB" -p "$BODY" --model sonnet --permission-mode acceptEdits \
          --allowedTools "Read,Write,Edit" || echo "[warn] スキル本文での実行も失敗"
    fi
    [ -f state/selection.json ] || echo "[info] selection.json なし(未ログイン等); 暫定ダイジェストで描画"
  else
    echo "[info] claude binary not found; 暫定ダイジェストで描画"
  fi

  if ! "$PY" scripts/render.py; then
    notify "⚠️ レンダリング失敗"
    echo "[fatal] render.py failed"; exit 1
  fi

  publish_digest

  MSG="$(cat state/notify.txt 2>/dev/null || echo '収集完了')"
  notify "$MSG"
  echo "=== done $(date '+%Y-%m-%d %H:%M:%S') ==="
} >> "$ROOT/state/run.log" 2>&1
