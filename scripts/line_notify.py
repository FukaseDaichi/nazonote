#!/usr/bin/env python3
"""Send the daily digest URL to LINE via the Messaging API.

Configuration is read from state/.env. Missing configuration is treated as a
non-fatal skip so the daily collection pipeline can keep running locally.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state")
ENV_PATH = os.path.join(STATE, ".env")
JST = datetime.timezone(datetime.timedelta(hours=9))


def parse_env_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("export "):
        line = line[len("export "):].lstrip()
    if "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return key, value


def load_env():
    values = {}
    try:
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                item = parse_env_line(line)
                if item:
                    values[item[0]] = item[1]
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[warn] failed to read {ENV_PATH}: {e}", file=sys.stderr)

    # Allow launchd or an interactive shell to override file values.
    for key in (
        "MOBILE_NOTIFY_ENABLED",
        "LINE_CHANNEL_ACCESS_TOKEN",
        "LINE_TO_USER_ID",
        "GITHUB_DAILY_URL_TEMPLATE",
    ):
        if os.environ.get(key):
            values[key] = os.environ[key]
    return values


def read_text(path, default=""):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return default


def today_str():
    today = read_text(os.path.join(STATE, "today.txt"))
    if today:
        return today
    return datetime.datetime.now(JST).strftime("%Y-%m-%d")


def send_line_message(token, to_user_id, text):
    payload = {
        "to": to_user_id,
        "messages": [{"type": "text", "text": text[:5000]}],
    }
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "nazonote-line-notifier/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as res:
        return res.status, res.read().decode("utf-8", errors="replace")


def main():
    env = load_env()
    if env.get("MOBILE_NOTIFY_ENABLED", "1").lower() in ("0", "false", "no", "off"):
        print("line_notify: disabled")
        return 0

    token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    to_user_id = env.get("LINE_TO_USER_ID", "").strip()
    template = env.get("GITHUB_DAILY_URL_TEMPLATE", "").strip()
    missing = [
        name
        for name, value in (
            ("LINE_CHANNEL_ACCESS_TOKEN", token),
            ("LINE_TO_USER_ID", to_user_id),
            ("GITHUB_DAILY_URL_TEMPLATE", template),
        )
        if not value
    ]
    if missing:
        print(f"line_notify: skipped; missing {', '.join(missing)}")
        return 0

    today = today_str()
    url = template.replace("{date}", today)
    summary = read_text(os.path.join(STATE, "notify.txt"), "収集完了")
    message = f"謎解きnote収集\n{summary}\n\n今日のダイジェスト:\n{url}"

    try:
        status, _body = send_line_message(token, to_user_id, message)
        print(f"line_notify: sent (status={status})")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[warn] line_notify failed: HTTP {e.code} {body}", file=sys.stderr)
    except Exception as e:
        print(f"[warn] line_notify failed: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
