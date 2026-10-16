# Starfleet voice console (XIAO ESP32S3 Sense)

A desk enclosure for a Seeed XIAO ESP32S3 Sense used as a Home Assistant voice satellite.
It has a sloped LCARS-style face, a two-part combadge inlay, a camera window with a mic grille,
and a USB-C power opening on the right side.

![front](preview_front.png)

Outside size: 84 × 64 mm footprint, 48 mm tall at the back.

## Parts (`stl/`)

| File | Print | Notes |
|---|---|---|
| `body.stl` | Open back on the bed, as exported | No supports needed. 0.2 mm layers, 3 walls. |
| `back.stl` | Outer face down | Has vents and a debossed "NCC-1701-D". |
| `sled.stl` | As exported (pins up) | Board holder. Glue it inside the face with its two pins in the holes. |
| `badge_oval.stl` | Flat | Gold or yellow filament. |
| `badge_delta.stl` | Flat | Silver or grey filament. Glue it on top of the oval. |

The raised LCARS panels are part of the body. Paint them with acrylic paint pens
(orange, peach and lilac look right) or leave them plain.

## Hardware

- Seeed XIAO ESP32S3 **Sense** (with its camera and mic expansion board fitted)
- 4 × M3 × 8 mm self-tapping screws (or M3 screws with heat-set inserts after widening the pilots)
- 4 × 8 mm stick-on rubber bumpers (optional)
- A USB-C cable and 5 V USB power supply

## Assembly

1. Glue the sled inside the face (CA glue). The camera hole should sit over the middle of the sled opening.
2. Push the board into the sled, camera side first, with the USB-C end toward the right-side opening.
   A dot of hot glue keeps it in place.
3. Glue the oval into the face pocket and the delta on top of it.
4. Screw the back plate on.

## Adjusting the fit

Everything is set by parameters at the top of `xiao_console.scad` (OpenSCAD 2021+).
The values most likely to need checking against your board:

- `cam_du`, `cam_dv`: move the camera hole if the lens isn't centred on the board.
- `usb_depth`: where the USB-C port sits behind the face.
- `usb_open`: opening size. The default of 13 × 7.5 mm fits most slim cables, but chunky plugs won't fit.

To export a part:

```
openscad -D 'part="body"' -o stl/body.stl xiao_console.scad
```
