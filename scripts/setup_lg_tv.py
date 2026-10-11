#!/usr/bin/env python3
"""Show /lcars-bridge on an LG (webOS) TV and switch back to the Apple TV.

Creates two Home Assistant scripts:
  script.lcars_show_on_tv      opens the TV's web browser on the LCARS dashboard
  script.lcars_back_to_apple_tv switches the TV back to the Apple TV's HDMI input

and adds a "Back to Apple TV" button below the Settings (or Motion On) button on
/lcars-bridge that only the TV's Home Assistant user can see.

Before running:
  1. Add the LG webOS TV integration so the TV has a media_player entity.
  2. Settings > People > Add person "LG TV", turn on "Allow person to login".
     Log the TV's Web Browser into HA as that user ("Keep me logged in").

Usage:
  pip install websockets
  HA_URL=http://homeassistant.local:8123 HA_TOKEN=<token> python3 setup_lg_tv.py \
      --tv media_player.lg_webos_tv --source "HDMI 1" \
      --dashboard-url http://192.168.1.10:8123/lcars-bridge

Safe to re-run: scripts are overwritten, the button is only added once.
"""

import argparse
import asyncio
import json
import os
import sys
import urllib.request

import websockets

from add_settings_button import card_lists, find_motion_card

SHOW_ID = "lcars_show_on_tv"
BACK_ID = "lcars_back_to_apple_tv"
SETTINGS_PATH = "/config/dashboard"


def scripts(tv, source, dashboard_url):
    return {
        SHOW_ID: {
            "alias": "Show LCARS Bridge on TV",
            "icon": "mdi:television-play",
            "mode": "single",
            "sequence": [{
                "action": "webostv.command",
                "data": {
                    "entity_id": tv,
                    "command": "system.launcher/open",
                    "payload": {"target": dashboard_url},
                },
            }],
        },
        BACK_ID: {
            "alias": "Back to Apple TV",
            "icon": "mdi:apple",
            "mode": "single",
            "sequence": [{
                "action": "media_player.select_source",
                "target": {"entity_id": tv},
                "data": {"source": source},
            }],
        },
    }


def save_script(url, token, object_id, config):
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/config/script/config/{object_id}",
        data=json.dumps(config).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        resp.read()


def find_anchor(config):
    """Return (parent_list, index) of the Settings button, else the Motion On card."""
    for cards in card_lists(config):
        for i, card in enumerate(cards):
            if isinstance(card, dict) and card.get("tap_action", {}).get("navigation_path") == SETTINGS_PATH:
                return cards, i
    return find_motion_card(config)


async def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tv", default="media_player.lg_webos_tv", help="TV media_player entity")
    parser.add_argument("--source", default="HDMI 1", help="TV source name of the Apple TV input")
    parser.add_argument("--dashboard-url", help="URL the TV opens (default: HA_URL/<dashboard>)")
    parser.add_argument("--user", default="LG TV", help="HA user the TV's browser is logged in as")
    parser.add_argument("--dashboard", default="lcars-bridge", help="dashboard to add the button to")
    args = parser.parse_args()

    url, token = os.environ.get("HA_URL"), os.environ.get("HA_TOKEN")
    if not url or not token:
        sys.exit("Set HA_URL and HA_TOKEN (Profile > Security > Long-lived access tokens).")
    path = args.dashboard.strip("/")
    dashboard_url = args.dashboard_url or f"{url.rstrip('/')}/{path}"
    if ".local" in dashboard_url:
        print(f"Note: the TV will open {dashboard_url}; if it can't resolve .local, pass --dashboard-url with an IP.")

    for object_id, config in scripts(args.tv, args.source, dashboard_url).items():
        save_script(url, token, object_id, config)
        print(f"Saved script.{object_id}")

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

        states = {s["entity_id"]: s for s in await call("get_states")}
        if args.tv not in states:
            tvs = [e for e in states if e.startswith("media_player.")]
            print(f"Warning: {args.tv} not found. media_player entities: {', '.join(tvs) or 'none'}")
        else:
            sources = states[args.tv]["attributes"].get("source_list") or []
            if sources and args.source not in sources:
                print(f"Warning: source {args.source!r} not on the TV. Sources: {', '.join(sources)}")

        users = [u for u in await call("config/auth/list") if u["name"].lower() == args.user.lower()]
        if not users:
            sys.exit(f"No HA user named {args.user!r}. Create it (Settings > People, allow login), "
                     "log the TV's browser in as it, then re-run to add the button.")
        user_id = users[0]["id"]

        config = await call("lovelace/config", url_path=path, force=False)
        if "strategy" in config:
            sys.exit("This dashboard is auto-generated; open it, choose 'Take control', then re-run.")
        if f"script.{BACK_ID}" in json.dumps(config):
            print(f"/{path} already has the Back to Apple TV button; scripts updated, done.")
            return

        cards, i = find_anchor(config)
        anchor = cards[i]
        button = {
            "type": "button",
            "name": "Apple TV",
            "icon": "mdi:apple",
            "show_state": False,
            "tap_action": {"action": "perform-action", "perform_action": f"script.{BACK_ID}"},
            "visibility": [{"condition": "user", "users": [user_id]}],
        }
        for key in ("uix", "card_mod"):
            if key in anchor:
                button[key] = anchor[key]

        with open(f"{path}.backup.json", "w") as f:
            json.dump(config, f, indent=2)
        cards.insert(i + 1, button)
        await call("lovelace/config/save", url_path=path, config=config)
        print(f"Added 'Apple TV' button (visible only to {users[0]['name']}) below "
              f"'{anchor.get('name', anchor.get('entity', 'anchor'))}' on /{path}.")
        print(f"Backup: {path}.backup.json. Refresh the dashboard in your browser.")


if __name__ == "__main__":
    asyncio.run(main())
