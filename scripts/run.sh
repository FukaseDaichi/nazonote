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

  MSG="$(cat state/notify.txt 2>/dev/null || echo '収集完了')"
  notify "$MSG"
  echo "=== done $(date '+%Y-%m-%d %H:%M:%S') ==="
} >> "$ROOT/state/run.log" 2>&1
