#!/usr/bin/env python3
"""Webhooks so a Sofabaton X1S can drive the LG TV and Apple TV through Home Assistant.

Creates script.apple_tv_control_center (holds Home on the Apple TV, which opens
Control Center) and three local-only webhook automations that run:
  script.lcars_show_on_tv        (from setup_lg_tv.py)
  script.lcars_back_to_apple_tv  (from setup_lg_tv.py)
  script.apple_tv_control_center

Each automation gets a random webhook ID the first time; re-runs keep the
existing ID so the X1S buttons keep working. The webhook URLs are printed at
the end; they act as passwords, so don't commit them.

Usage:
  HA_URL=http://192.168.1.10:8123 HA_TOKEN=<token> python3 setup_x1s_webhooks.py \
      --remote remote.apple_tv
"""

import argparse
import json
import os
import secrets
import sys
import urllib.error
import urllib.request

CONTROL_CENTER_ID = "apple_tv_control_center"

WEBHOOKS = [
    # (automation id, alias, script it runs, X1S button)
    ("x1s_show_lcars_bridge", "X1S: Show LCARS Bridge on TV", "script.lcars_show_on_tv", "Show Bridge"),
    ("x1s_back_to_apple_tv", "X1S: Back to Apple TV", "script.lcars_back_to_apple_tv", "Back to Apple TV"),
    ("x1s_apple_tv_control_center", "X1S: Apple TV Control Center",
     f"script.{CONTROL_CENTER_ID}", "Control Center"),
]


def api(url, token, path, config=None):
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/config/{path}",
        data=json.dumps(config).encode() if config is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST" if config is not None else "GET",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read() or "null")


def existing_webhook_id(url, token, automation_id):
    try:
        config = api(url, token, f"automation/config/{automation_id}")
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise
    for trigger in config.get("triggers", config.get("trigger", [])):
        if trigger.get("webhook_id"):
            return trigger["webhook_id"]
    return None


def automation(alias, script, webhook_id):
    return {
        "alias": alias,
        "description": "Sofabaton X1S button (local-only webhook).",
        "mode": "single",
        "triggers": [{
            "trigger": "webhook",
            "webhook_id": webhook_id,
            "allowed_methods": ["POST", "PUT"],
            "local_only": True,
        }],
        "conditions": [],
        "actions": [{"action": "script.turn_on", "target": {"entity_id": script}, "continue_on_error": True}],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--remote", required=True, help="Apple TV remote entity, e.g. remote.apple_tv")
    parser.add_argument("--webhook-host", help="base URL for printed webhook URLs (default: HA_URL)")
    args = parser.parse_args()

    url, token = os.environ.get("HA_URL"), os.environ.get("HA_TOKEN")
    if not url or not token:
        sys.exit("Set HA_URL and HA_TOKEN (Profile > Security > Long-lived access tokens).")

    api(url, token, f"script/config/{CONTROL_CENTER_ID}", {
        "alias": "Apple TV Control Center",
        "icon": "mdi:apple",
        "mode": "single",
        "sequence": [{
            "action": "remote.send_command",
            "target": {"entity_id": args.remote},
            "data": {"command": "home", "hold_secs": 1},
            "continue_on_error": True,
        }],
    })
    print(f"Saved script.{CONTROL_CENTER_ID}")

    base = (args.webhook_host or url).rstrip("/")
    urls = []
    for automation_id, alias, script, button in WEBHOOKS:
        webhook_id = existing_webhook_id(url, token, automation_id) or secrets.token_urlsafe(24)
        try:
            api(url, token, f"automation/config/{automation_id}", automation(alias, script, webhook_id))
        except urllib.error.HTTPError as err:
            sys.exit(f"Saving automation {automation_id} failed: HTTP {err.code} {err.read().decode()[:200]}")
        print(f"Saved automation {automation_id}")
        urls.append((button, f"{base}/api/webhook/{webhook_id}"))

    print("\nX1S webhook URLs (POST, local network only; keep these private):")
    for button, hook in urls:
        print(f"  {button}: {hook}")


if __name__ == "__main__":
    main()
