#!/usr/bin/env python3
"""Read and write Home Assistant dashboards and entity states.

Usage (HA_URL and HA_TOKEN must be set):
  python3 ha_dashboard.py list                       # list dashboards
  python3 ha_dashboard.py get <path> > dash.json     # dump a dashboard's config
  python3 ha_dashboard.py save <path> dash.json      # save it back (backs up first)
  python3 ha_dashboard.py states [filter]            # entity ids, state, last_updated
"""

import asyncio
import json
import os
import sys
import time

import websockets


async def main():
    url, token = os.environ.get("HA_URL"), os.environ.get("HA_TOKEN")
    if not url or not token or len(sys.argv) < 2:
        sys.exit(__doc__)
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

        cmd, args = sys.argv[1], sys.argv[2:]
        if cmd == "list":
            for d in await call("lovelace/dashboards/list"):
                print(f"{d['url_path']:30} {d.get('title', '')}")
        elif cmd == "get":
            print(json.dumps(await call("lovelace/config", url_path=args[0], force=False), indent=2))
        elif cmd == "save":
            path, file = args
            backup = f"{path}.backup-{int(time.time())}.json"
            with open(backup, "w") as f:
                json.dump(await call("lovelace/config", url_path=path, force=False), f, indent=2)
            with open(file) as f:
                await call("lovelace/config/save", url_path=path, config=json.load(f))
            print(f"Saved /{path}. Previous version backed up to {backup}")
        elif cmd == "states":
            needle = args[0].lower() if args else ""
            for s in await call("get_states"):
                if needle in s["entity_id"].lower():
                    print(f"{s['entity_id']:50} {s['state']:15} updated {s['last_updated']}")
        else:
            sys.exit(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
