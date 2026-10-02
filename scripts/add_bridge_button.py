#!/usr/bin/env python3
"""Add a "Bridge" button (navigates to /lcars-bridge) to every view of a dashboard.

Usage:
  pip install websockets
  HA_URL=http://homeassistant.local:8123 HA_TOKEN=<token> python3 add_bridge_button.py [dashboard-path]

Run without a dashboard path to list the dashboards. A backup of the old
config is written to <dashboard-path>.backup.json before saving.
"""

import asyncio
import json
import os
import sys

import websockets

TARGET = "/lcars-bridge"
BUTTON = {
    "type": "button",
    "name": "Bridge",
    "icon": "mdi:star-four-points",
    "show_state": False,
    "tap_action": {"action": "navigate", "navigation_path": TARGET},
    "uix": {"class": "button-large"},
}


def has_button(obj):
    return TARGET in json.dumps(obj)


def add_to_view(view):
    """Insert the button at the top of a view. Returns True if changed."""
    if has_button(view):
        return False
    if "strategy" in view:
        raise SystemExit(f"View '{view.get('title', '?')}' is auto-generated; take control of the dashboard first.")
    if view.get("type") == "sections":
        sections = view.setdefault("sections", [])
        if not sections:
            sections.append({"type": "grid", "cards": []})
        sections[0].setdefault("cards", []).insert(0, BUTTON)
    elif view.get("type") == "panel" and view.get("cards"):
        # A panel view only shows its first card, so stack the button above it.
        view["cards"][0] = {"type": "vertical-stack", "cards": [BUTTON, view["cards"][0]]}
    else:
        view.setdefault("cards", []).insert(0, BUTTON)
    return True


async def main():
    url, token = os.environ.get("HA_URL"), os.environ.get("HA_TOKEN")
    if not url or not token:
        sys.exit("Set HA_URL and HA_TOKEN (Profile > Security > Long-lived access tokens).")
    ws_url = url.rstrip("/").replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"

    async with websockets.connect(ws_url, max_size=None) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv())["type"] != "auth_ok":
            sys.exit("Authentication failed; check HA_TOKEN.")

        msg_id = 0

        async def call(type_, **payload):
            nonlocal msg_id
            msg_id += 1
            await ws.send(json.dumps({"id": msg_id, "type": type_, **payload}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == msg_id:
                    break
            if not msg.get("success"):
                raise SystemExit(f"{type_} failed: {msg.get('error', {}).get('message', msg)}")
            return msg["result"]

        dashboards = await call("lovelace/dashboards/list")
        if len(sys.argv) < 2:
            print("Dashboards (pass one of these paths as the argument):")
            for d in dashboards:
                print(f"  {d['url_path']:30} {d.get('title', '')}")
            return

        path = sys.argv[1].strip("/")
        config = await call("lovelace/config", url_path=path, force=False)
        if "strategy" in config:
            sys.exit("This dashboard is auto-generated; open it, choose 'Take control', then re-run.")

        backup = f"{path}.backup.json"
        with open(backup, "w") as f:
            json.dump(config, f, indent=2)

        changed = sum(add_to_view(v) for v in config.get("views", []))
        if not changed:
            print(f"Every view of /{path} already links to {TARGET}; nothing to do.")
            return
        await call("lovelace/config/save", url_path=path, config=config)
        print(f"Added the Bridge button to {changed} view(s) of /{path}. Backup: {backup}")
        print("Refresh the dashboard in your browser.")


if __name__ == "__main__":
    asyncio.run(main())
