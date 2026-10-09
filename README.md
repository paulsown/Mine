# LCARS dashboard for Home Assistant

Installs [HA-LCARS](https://github.com/th3jesta/ha-lcars) (Star Trek LCARS theme) and an LCARS dashboard.

## 1. Prerequisites (in the HA UI)

1. **HACS → search "UI eXtension" → Download**, restart HA, then
   *Settings → Devices & services → Add integration → UI eXtension*.
2. **HACS → search "LCARS" → Download** (the HA-LCARS theme).
3. Make sure `configuration.yaml` loads themes, then restart:
   ```yaml
   frontend:
     themes: !include_dir_merge_named themes
   ```

## 2. Run the installer

Create a long-lived token (*Profile → Security → Long-lived access tokens*), then from any machine that can reach HA:

```bash
pip install websockets pyyaml
HA_URL=http://homeassistant.local:8123 HA_TOKEN=<token> python3 scripts/install_lcars.py
```

It is safe to re-run. It:
- adds the Antonio font and `lcars.js` as dashboard resources
- adds the Time & Date integration (`sensor.time`, the LCARS clock)
- creates helpers `input_boolean.lcars_sound`, `input_boolean.lcars_texture`,
  `input_number.lcars_vertical`, `input_number.lcars_horizontal`, `input_number.lcars_menu_font`
- creates the **LCARS** dashboard at `/lcars-bridge` from `homeassistant/dashboards/lcars.yaml`
- sets **LCARS Default** as the backend theme (only once UIX + theme are detected)

Hard-refresh the browser (Ctrl+Shift+R) afterwards.

## Manual alternative (no script)

- Copy `homeassistant/packages/lcars.yaml` to `<config>/packages/` and enable packages
  (`homeassistant: packages: !include_dir_named packages`). It creates the same helpers,
  an optional `sensor.lcars_header`, and an automation that applies the theme on startup.
  Use this **or** the script's helpers, not both, or you'll get `_2` duplicate entities.
- *Settings → Dashboards → ⋮ → Resources*: add the two URLs from `RESOURCES` in the script
  (font as *Stylesheet*, `lcars.js` as *JavaScript module*).
- Add the *Time & Date* integration (sensor type *Time*).
- Create a dashboard, open *⋮ → Edit → ⋮ → Raw configuration editor*, paste `homeassistant/dashboards/lcars.yaml`.

Tip: exclude `sensor.time` from the recorder so it doesn't write every minute.

## LG TV: show the bridge, switch back to Apple TV

`scripts/setup_lg_tv.py` creates two HA scripts and a TV-only dashboard button:

- `script.lcars_show_on_tv` opens the LG's Web Browser on `/lcars-bridge` (the TV leaves the HDMI input)
- `script.lcars_back_to_apple_tv` switches the TV back to the Apple TV's HDMI input
- an **Apple TV** button below Settings on `/lcars-bridge` that runs it, visible only to the `LG TV` user

Setup:
1. Add the *LG webOS TV* integration.
2. *Settings → People → Add person* `LG TV`, allow login. On the TV, open Web Browser,
   go to the dashboard and log in as `LG TV` ("Keep me logged in"). Bookmark it.
3. Run (use your TV entity, the Apple TV's source name as shown in the TV's source list,
   and an IP-based URL if the TV can't resolve `.local`):
   ```bash
   HA_URL=http://homeassistant.local:8123 HA_TOKEN=<token> python3 scripts/setup_lg_tv.py \
       --tv media_player.lg_webos_tv --source "HDMI 1" \
       --dashboard-url http://192.168.1.10:8123/lcars-bridge
   ```

To trigger it from the Apple TV's Control Center: add the *HomeKit Bridge* integration and include
`script.lcars_show_on_tv` (it appears in Apple Home as a switch), then in the Apple Home app create a
scene "Bridge" that turns it on. Hold the TV button on the Siri Remote → Home → Bridge, or "Hey Siri, Bridge".
