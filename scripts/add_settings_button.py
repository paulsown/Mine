#!/usr/bin/env python3
"""Add a "Settings" button directly below the "Motion On" button on /lcars-bridge.

The button opens Home Assistant's Settings page. If the Motion button is an
LCARdS button, the Settings button is a copy of it (same preset, colours and
fonts) with a new label and tap action; otherwise the Motion button's uix /
card_mod styling is copied onto a plain button card.

The Motion On toggle is usually repeated on every view's sidebar. Identical
copies are all treated as targets, so every view gets a Settings button. When
the toggle sits in a named grid area (e.g. an lcards-layout-card with
grid-template-areas), a matching "settings" row is added below it so the new
button gets its own slot instead of being squeezed into an implicit row.

Usage:
  pip install websockets
  HA_URL=http://homeassistant.local:8123 HA_TOKEN=<token> python3 add_settings_button.py [dashboard-path]

A backup of the old config is written to <dashboard-path>.backup-<timestamp>.json
before saving.
"""

import asyncio
import copy
import json
import os
import sys
import time

import websockets

SETTINGS_PATH = "/config/dashboard"
SETTINGS_AREA = "settings"
BUTTON = {
    "type": "button",
    "name": "Settings",
    "icon": "mdi:cog",
    "show_state": False,
    "tap_action": {"action": "navigate", "navigation_path": SETTINGS_PATH},
}


def card_lists(node):
    """Yield (owner, cards) for every list of cards in the dashboard config."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "cards" and isinstance(value, list):
                yield node, value
            yield from card_lists(value)
    elif isinstance(node, list):
        for item in node:
            yield from card_lists(item)


def is_leaf(card):
    return not any(card_lists(card))


def label(card):
    """Best human-readable label for a card."""
    text = card.get("text", {}).get("label", {}).get("content") if isinstance(card.get("text"), dict) else None
    return card.get("name") or text or card.get("entity") or card.get("type")


def signature(card):
    """A card's identity, ignoring where it sits, where it links and its decorative code number."""
    c = copy.deepcopy(card)
    for key in ("view_layout", "tap_action"):
        c.pop(key, None)
    if isinstance(c.get("text"), dict):
        c["text"].pop("code", None)
    return json.dumps(c, sort_keys=True)


def find_motion_cards(config):
    """Return [(owner, cards, index), ...] for the Motion On card(s), or exit listing the candidates."""
    exact, loose = [], []
    for owner, cards in card_lists(config):
        for i, card in enumerate(cards):
            if not isinstance(card, dict) or not is_leaf(card):
                continue
            text = json.dumps(card).lower()
            if "motion on" in text:
                exact.append((owner, cards, i))
            elif "motion" in text:
                loose.append((owner, cards, i))
    for matches in (exact, loose):
        if not matches:
            continue
        # One card, or the same card repeated on several views: all are targets.
        if len({signature(cards[i]) for _, cards, i in matches}) == 1:
            return matches
        print("Found several different Motion cards; can't tell which one is 'Motion On':")
        for _, cards, i in matches:
            c = cards[i]
            code = c.get("text", {}).get("code", {}).get("content") if isinstance(c.get("text"), dict) else None
            nav = c.get("tap_action", {}).get("navigation_path")
            print(f"  {c.get('type')}: label={str(label(c))[:40]!r} entity={c.get('entity')!r} code={code!r} tap={nav!r}")
        sys.exit("Rename the right one to 'Motion On' (or tell Claude which one) and re-run.")
    sys.exit("No Motion card found on this dashboard.")


def make_button(motion):
    if motion.get("type") == "custom:lcards-button" and isinstance(motion.get("text", {}).get("label"), dict):
        button = copy.deepcopy(motion)
        button["text"]["label"]["content"] = "Settings"
        button["tap_action"] = {"action": "navigate", "navigation_path": SETTINGS_PATH}
        for key in ("hold_action", "double_tap_action", "entity"):
            button.pop(key, None)
        return button
    button = copy.deepcopy(BUTTON)
    for key in ("uix", "card_mod", "view_layout"):
        if key in motion:
            button[key] = copy.deepcopy(motion[key])
    return button


def last_track(rows):
    """Return the last track of a grid-template-rows value, respecting parentheses."""
    depth, start = 0, 0
    for i, ch in enumerate(rows):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch.isspace() and depth == 0:
            start = i + 1
    return rows[start:].strip()


def add_grid_row(owner, button, motion):
    """Give the button its own named grid row below the Motion card's, if it has one."""
    area = motion.get("view_layout", {}).get("grid-area")
    layout = owner.get("layout", {})
    areas = layout.get("grid-template-areas", "").strip()
    if not area or f'"{area}"' not in areas or not areas.endswith(f'"{area}"'):
        button.get("view_layout", {}).pop("grid-area", None)
        return
    layout["grid-template-areas"] = f'{areas} "{SETTINGS_AREA}"'
    if layout.get("grid-template-rows"):
        rows = layout["grid-template-rows"].strip()
        layout["grid-template-rows"] = f"{rows} {last_track(rows)}"
    button["view_layout"]["grid-area"] = SETTINGS_AREA


def add_settings(config):
    """Insert a Settings button below every Motion On card. Returns the number added."""
    matches = find_motion_cards(config)
    for owner, cards, i in matches:
        motion = cards[i]
        button = make_button(motion)
        add_grid_row(owner, button, motion)
        cards.insert(i + 1, button)
    return len(matches)


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

        backup = f"{path}.backup-{time.strftime('%Y%m%d-%H%M%S')}.json"
        original = json.dumps(config, indent=2)
        added = add_settings(config)
        with open(backup, "w") as f:
            f.write(original)
        await call("lovelace/config/save", url_path=path, config=config)
        print(f"Added {added} Settings button(s) below 'Motion On' on /{path}.")
        print(f"Backup: {backup}. Refresh the dashboard in your browser.")


if __name__ == "__main__":
    asyncio.run(main())
