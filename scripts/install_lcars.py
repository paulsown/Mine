#!/usr/bin/env python3
"""Set up an HA-LCARS dashboard on a Home Assistant instance.

The script does everything that the Home Assistant API allows:
  * registers the Antonio font and lcars.js as dashboard resources
  * adds the Time & Date integration (sensor.time) for the LCARS clock
  * creates the LCARS helper entities if they are missing
  * creates the "LCARS" dashboard from homeassistant/dashboards/lcars.yaml
  * sets LCARS Default as the backend theme

Two things need HACS or file access and are only checked, not installed:
the UI eXtension (UIX) integration and the HA-LCARS theme itself.

Usage:
  pip install websockets pyyaml
  HA_URL=http://homeassistant.local:8123 HA_TOKEN=<long-lived token> \
      python3 scripts/install_lcars.py
"""

import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import websockets
import yaml

DASHBOARD_FILE = Path(__file__).resolve().parent.parent / "homeassistant/dashboards/lcars.yaml"
DASHBOARD_URL_PATH = "lcars-bridge"
THEME = "LCARS Default"

RESOURCES = [
    ("https://fonts.googleapis.com/css2?family=Antonio:wght@400;700&display=swap", "css"),
    ("https://cdn.jsdelivr.net/gh/th3jesta/ha-lcars@js-main/lcars.js", "module"),
]

HELPERS = [
    ("input_boolean", {"name": "LCARS Sound", "icon": "mdi:volume-high"}),
    ("input_boolean", {"name": "LCARS Texture", "icon": "mdi:texture-box"}),
    ("input_number", {"name": "LCARS Vertical", "min": 26, "max": 60, "step": 1, "initial": 26, "mode": "slider"}),
    ("input_number", {"name": "LCARS Horizontal", "min": 6, "max": 60, "step": 1, "initial": 6, "mode": "slider"}),
    ("input_number", {"name": "LCARS Menu Font", "min": 12, "max": 36, "step": 1, "initial": 20, "mode": "slider"}),
]


class HA:
    def __init__(self, url, token):
        self.url = url.rstrip("/")
        self.token = token
        self.msg_id = 0

    def rest(self, method, path, body=None):
        req = urllib.request.Request(
            f"{self.url}{path}",
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read() or "null")

    async def connect(self):
        ws_url = self.url.replace("https://", "wss://").replace("http://", "ws://") + "/api/websocket"
        self.ws = await websockets.connect(ws_url, max_size=None)
        await self.ws.recv()  # auth_required
        await self.ws.send(json.dumps({"type": "auth", "access_token": self.token}))
        msg = json.loads(await self.ws.recv())
        if msg["type"] != "auth_ok":
            sys.exit(f"Authentication failed: {msg.get('message', msg)}")
        print(f"Connected to Home Assistant {msg.get('ha_version', '')}")

    async def call(self, type_, **payload):
        self.msg_id += 1
        await self.ws.send(json.dumps({"id": self.msg_id, "type": type_, **payload}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == self.msg_id:
                break
        if not msg.get("success"):
            raise RuntimeError(f"{type_}: {msg.get('error', {}).get('message', msg)}")
        return msg.get("result")


async def ensure_resources(ha):
    try:
        existing = {r["url"] for r in await ha.call("lovelace/resources")}
    except RuntimeError as err:
        print(f"! Could not list resources ({err}); is Lovelace in YAML mode? Add them manually.")
        return
    for url, res_type in RESOURCES:
        if url in existing:
            print(f"= resource already present: {url}")
        else:
            await ha.call("lovelace/resources/create", url=url, res_type=res_type)
            print(f"+ added resource: {url}")


def ensure_time_date(ha):
    if entity_exists(ha, "sensor.time"):
        print("= sensor.time already exists")
        return
    flow = ha.rest("POST", "/api/config/config_entries/flow", {"handler": "time_date"})
    # Newer versions show a menu/form asking which sensor to create.
    for _ in range(3):
        if flow.get("type") not in ("form", "menu"):
            break
        body = {"display_option": "time"} if flow["type"] == "form" else {"next_step_id": flow["menu_options"][0]}
        flow = ha.rest("POST", f"/api/config/config_entries/flow/{flow['flow_id']}", body)
    if flow.get("type") == "create_entry":
        print("+ added Time & Date integration (sensor.time)")
    else:
        print(f"! Time & Date setup returned {flow.get('type')}: {flow.get('reason', '')}; add it in the UI.")


def entity_exists(ha, entity_id):
    try:
        ha.rest("GET", f"/api/states/{entity_id}")
        return True
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return False
        raise


async def ensure_helpers(ha):
    for domain, data in HELPERS:
        entity_id = f"{domain}.{data['name'].lower().replace(' ', '_')}"
        if entity_exists(ha, entity_id):
            print(f"= {entity_id} already exists")
        else:
            await ha.call(f"{domain}/create", **data)
            print(f"+ created {entity_id}")


async def ensure_dashboard(ha):
    config = yaml.safe_load(DASHBOARD_FILE.read_text())
    dashboards = await ha.call("lovelace/dashboards/list")
    if not any(d["url_path"] == DASHBOARD_URL_PATH for d in dashboards):
        await ha.call(
            "lovelace/dashboards/create",
            url_path=DASHBOARD_URL_PATH,
            title="LCARS",
            icon="mdi:star-four-points",
            show_in_sidebar=True,
            require_admin=False,
            mode="storage",
        )
        print(f"+ created dashboard /{DASHBOARD_URL_PATH}")
    await ha.call("lovelace/config/save", url_path=DASHBOARD_URL_PATH, config=config)
    print(f"+ saved dashboard layout to /{DASHBOARD_URL_PATH}")


async def check_prereqs(ha):
    ok = True
    entries = ha.rest("GET", "/api/config/config_entries/entry")
    if not any(e["domain"] == "uix" for e in entries):
        ok = False
        print("! UI eXtension (UIX) is not set up. Install it from HACS, restart, then add the")
        print("  'UI eXtension' integration under Settings > Devices & services.")
    themes = (await ha.call("frontend/get_themes"))["themes"]
    if THEME not in themes:
        ok = False
        print(f"! Theme '{THEME}' not found. Install 'HA-LCARS' from HACS (Frontend/Theme) and make sure")
        print("  configuration.yaml has `frontend: themes: !include_dir_merge_named themes`, then restart.")
    return ok


async def main():
    url, token = os.environ.get("HA_URL"), os.environ.get("HA_TOKEN")
    if not url or not token:
        sys.exit("Set HA_URL and HA_TOKEN (Profile > Security > Long-lived access tokens).")
    ha = HA(url, token)
    await ha.connect()

    prereqs_ok = await check_prereqs(ha)
    await ensure_resources(ha)
    ensure_time_date(ha)
    await ensure_helpers(ha)
    await ensure_dashboard(ha)

    if prereqs_ok:
        await ha.call("call_service", domain="frontend", service="set_theme", service_data={"name": THEME, "mode": "dark"})
        print(f"+ backend theme set to {THEME}")
        print(f"\nDone. Open {ha.url}/{DASHBOARD_URL_PATH} and hard-refresh (Ctrl+Shift+R).")
    else:
        print("\nDashboard is in place; finish the '!' items above, restart, and re-run this script.")
    await ha.ws.close()


if __name__ == "__main__":
    asyncio.run(main())
