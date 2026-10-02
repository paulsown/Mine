#!/usr/bin/env python3
"""Add a "Settings" button directly below the "Motion On" button on /lcars-bridge.

The button opens Home Assistant's Settings page and copies the LCARS styling
(uix / card_mod class) of the Motion button so the two match.

Usage:
  pip install websockets
  HA_URL=http://homeassistant.local:8123 HA_TOKEN=<token> python3 add_settings_button.py [dashboard-path]

A backup of the old config is written to <dashboard-path>.backup.json before saving.
"""

import asyncio
import json
import os
import sys

import websockets

SETTINGS_PATH = "/config/dashboard"
BUTTON = {
    "type": "button",
    "name": "Settings",
    "icon": "mdi:cog",
    "show_state": False,
    "tap_action": {"action": "navigate", "navigation_path": SETTINGS_PATH},
}


def card_lists(node):
    """Yield every list of cards in the dashboard config."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "cards" and isinstance(value, list):
                yield value
            yield from card_lists(value)
    elif isinstance(node, list):
        for item in node:
            yield from card_lists(item)


def is_leaf(card):
    return not any(card_lists(card))


def find_motion_card(config):
    """Return (parent_list, index) of the Motion On card, or exit listing the candidates."""
    exact, loose = [], []
    for cards in card_lists(config):
        for i, card in enumerate(cards):
            if not isinstance(card, dict) or not is_leaf(card):
                continue
            text = json.dumps(card).lower()
            if "motion on" in text:
                exact.append((cards, i))
            elif "motion" in text:
                loose.append((cards, i))
    for matches in (exact, loose):
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            print("Found several Motion cards; can't tell which one is 'Motion On':")
            for cards, i in matches:
                c = cards[i]
                print(f"  {c.get('type')}: name={c.get('name')!r} entity={c.get('entity')!r}")
            sys.exit("Rename the right one to 'Motion On' (or tell Claude which one) and re-run.")
    sys.exit("No Motion card found on this dashboard.")


async def main():
    url, token = os.environ.get("HA_URL"), os.environ.get("HA_TOKEN")
    if not url or not token:
        sys.exit("Set HA_URL and HA_TOKEN (Profile > Security > Long-lived access tokens).")
    path = (sys.argv[1] if len(sys.argv) > 1 else "lcars-bridge").strip("/")
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

        config = await call("lovelace/config", url_path=path, force=False)
        if "strategy" in config:
            sys.exit("This dashboard is auto-generated; open it, choose 'Take control', then re-run.")
        if SETTINGS_PATH in json.dumps(config):
            print(f"/{path} already has a Settings button; nothing to do.")
            return

        cards, i = find_motion_card(config)
        motion = cards[i]
        button = dict(BUTTON)
        for key in ("uix", "card_mod"):
            if key in motion:
                button[key] = motion[key]

        with open(f"{path}.backup.json", "w") as f:
            json.dump(config, f, indent=2)
        cards.insert(i + 1, button)
        await call("lovelace/config/save", url_path=path, config=config)
        print(f"Added Settings below '{motion.get('name', motion.get('entity', 'Motion'))}' on /{path}.")
        print(f"Backup: {path}.backup.json. Refresh the dashboard in your browser.")


if __name__ == "__main__":
    asyncio.run(main())
