// Starfleet desk console for a Seeed XIAO ESP32S3 Sense (Home Assistant voice satellite)
//
// A sloped case with a flat LCARS face panel that drops into a pocket on the front.
// The face panel is the only multi-colour part: it prints face-down and the colours
// are only in its first three layers, so a 4-colour printer swaps filament on just
// those layers. Everything else prints in one colour.
//
// Colours: black (panel background), orange (LCARS bars), gold (combadge oval and
// buttons), silver (combadge delta, LCARS pill, camera window frame, and the case).
//
// Parts (set `part` or use -D part="\"body\"" on the command line):
//   assembly      everything in place, for looking at
//   body          main shell, rotated to print on its open back      (silver)
//   back          back plate                                          (silver)
//   sled          board holder, glued inside the face                 (any)
//   panel_black   face panel, background and body                     \
//   panel_orange  face panel, orange colour layer                      | load together as
//   panel_gold    face panel, gold colour layer                        | one multi-part object
//   panel_silver  face panel, silver colour layer                     /
//
// All sizes in mm. Check the "board" and "usb" values against your own board
// before printing; they are the ones most likely to need a nudge.

part = "assembly";

/* [Case] */
W    = 84;     // width at the floor
D    = 64;     // depth front to back
Hf   = 16;     // height of the front edge
Hb   = 48;     // height of the back edge
wall = 2.4;    // side, front, floor walls
top_wall = 3.0; // sloped face, including the panel pocket
taper = 0.10;  // side walls lean in this much per mm of height

/* [Face panel] */
plate_t  = 1.2;   // panel thickness (pocket depth)
color_t  = 0.6;   // colour layers at the panel's face (3 layers at 0.2 mm)
margin   = 3;     // case border left around the panel
plate_fit = 0.15; // pocket clearance per side

/* [XIAO ESP32S3 Sense] */
board_w  = 21.0;   // along the USB axis
board_h  = 17.8;
stack    = 15.0;   // camera top to bottom of the XIAO
board_v  = 38;     // board centre, measured up the face from its front edge
board_gap = 0.9;   // space left between the USB-C end and the side wall
fit      = 0.2;    // clearance per side in the sled
cam_du   = 0;      // camera lens offset from board centre (along USB axis, + toward USB)
cam_dv   = 0;      // camera lens offset from board centre (up the face)
cam_d    = 8.6;    // camera hole diameter
usb_depth = 12.4;  // USB-C centre, measured inward from the camera top
usb_open  = [13, 7.5]; // opening for the plug overmould (along face, across face)

/* [Hardware] */
screw_pilot = 2.6;     // M3 self-tapping screw into plastic
screw_clear = 3.4;

$fn = 64;
eps = 0.01;

theta = atan((Hb - Hf) / D);
L     = sqrt(D * D + (Hb - Hf) * (Hb - Hf));   // length of the face
side_k = sqrt(1 + taper * taper);

// half-width of the outside of the case at height z
function hw_out(z) = W / 2 - taper * z;
// half-width of the inside of the case at height z
function hw_in(z)  = W / 2 - wall * side_k - taper * z;
// model height of a point on the face, `d` mm inward from the outer surface
function face_z(v, d = 0) = Hf + v * sin(theta) - d * cos(theta);
// half-width of the face itself
function face_hw(v) = hw_out(face_z(v));

// Board placement: USB-C end sits `board_gap` short of the inner side wall
// at the board's highest corner.
board_top_z = face_z(board_v + board_h / 2, top_wall);
bx = hw_in(board_top_z) - board_gap - 0.6 - board_w / 2;   // 0.6 = USB-C overhang
bv = board_v;

// ---------- basic solids ----------

// Prism with tapered sides and a sloped top running from z=zf at y0 to z=zb at y1.
module wedge(hw0, y0, y1, z0, zf, zb) {
    hull() for (p = [[y0, zf], [y1, zb]]) for (s = [-1, 1]) {
        translate([s * (hw0 - taper * z0), p[0], z0]) cube(eps, center = true);
        translate([s * (hw0 - taper * p[1]), p[0], p[1]]) cube(eps, center = true);
    }
}

module outer_solid() wedge(W / 2, 0, D, 0, Hf, Hb);

module inner_void() {
    dz = top_wall / cos(theta);
    y0 = wall; y1 = D + 1;
    wedge(W / 2 - wall * side_k, y0, y1, wall,
          Hf + y0 * tan(theta) - dz, Hf + y1 * tan(theta) - dz);
}

// Local frame on the face: x = across, y = up the slope, z = out of the face.
module face_frame() translate([0, 0, Hf]) rotate([theta, 0, 0]) children();

// ---------- 2D artwork (face coordinates) ----------

function bez(p0, p1, p2, n = 12) =
    [for (i = [0 : n]) let(t = i / n)
        (1 - t) * (1 - t) * p0 + 2 * (1 - t) * t * p1 + t * t * p2];

badge_at = [-6, 26];

module delta2d() {
    // TNG combadge arrowhead, 22 wide x 30 tall, origin at its middle
    pts = concat(
        bez([0, 16], [7, 3], [11, -14]),     // right edge
        bez([11, -14], [5, -9], [0, -6]),    // notch, right half
        bez([0, -6], [-5, -9], [-11, -14]),  // notch, left half
        bez([-11, -14], [-7, 3], [0, 16])    // left edge
    );
    translate(badge_at) polygon(pts);
}

module oval2d() translate(badge_at + [0, -2]) scale([16, 8.5]) circle(1);

module rrect(x0, y0, x1, y1, r) {
    translate([x0 + r, y0 + r]) offset(r = r) square([x1 - x0 - 2 * r, y1 - y0 - 2 * r]);
}

module pill(x0, y0, x1, y1) {
    r = (y1 - y0) / 2;
    hull() for (x = [x0 + r, x1 - r]) translate([x, y0 + r]) circle(r);
}

// LCARS elbow: vertical bar down the left, sweeping into a bar along the top.
module elbow2d(x0, y0, x1, ytop, bw, bh, ro, ri) {
    intersection() {
        union() {
            translate([x0, y0]) square([bw, ytop - y0]);
            translate([x0, ytop - bh]) square([x1 - x0, bh]);
        }
        rrect(x0, y0 - ro - 1, x1 + ro + 1, ytop, ro);
    }
    // inner fillet
    translate([x0 + bw, ytop - bh - ri]) difference() {
        square([ri, ri]);
        translate([ri, 0]) circle(ri);
    }
}

// Outline of the face panel
module plate2d() {
    v0 = margin; v1 = L - margin;
    polygon([[-(face_hw(v0) - margin), v0], [face_hw(v0) - margin, v0],
             [face_hw(v1) - margin, v1], [-(face_hw(v1) - margin), v1]]);
}

module window_outline2d() {
    x1 = min(bx + 11.5, face_hw(bv + 11) - margin - 0.5);
    difference() {
        rrect(bx - 12, bv - 11, x1, bv + 11, 3);
        offset(delta = -0.9) rrect(bx - 12, bv - 11, x1, bv + 11, 3);
    }
}

top = 66;
lx  = -face_hw(top) + margin + 1.8;   // left edge of the LCARS elbow

module orange2d() {
    elbow2d(lx, 22, 4, top, 9, 6, 9, 4);
    translate([lx, 6]) square([9, 14.5]);
    translate([5.5, top - 6]) square([15, 6]);
    translate([lx + 11, 5]) square([31, 3]);
}

module gold2d() {
    difference() { oval2d(); offset(delta = 0.4) delta2d(); }
    for (i = [0 : 2]) pill(18 - i * 3, 5 + i * 7, face_hw(24) - margin - 1.8, 10 + i * 7);
}

module silver2d() {
    delta2d();
    pill(22, top - 6, face_hw(top) - margin - 1.8, top);
    window_outline2d();
}

module mic_slots2d() {
    for (s = [-1, 1]) for (i = [0 : 2])
        translate([bx + cam_du + s * (5.0 + i * 1.9) - 0.6, bv - 6]) square([1.2, 12]);
}

// holes shared by the panel and the case
module holes2d() {
    translate([bx + cam_du, bv + cam_dv]) circle(d = cam_d);
    mic_slots2d();
}

// ---------- face panel ----------
// Built in face coordinates: z = 0 is the visible surface, z = -plate_t the back.

module panel_colour(which) {
    translate([0, 0, -color_t]) linear_extrude(color_t) difference() {
        intersection() {
            plate2d();
            if (which == "orange") orange2d();
            else if (which == "gold") gold2d();
            else if (which == "silver") silver2d();
        }
        holes2d();
    }
}

module panel_black() {
    difference() {
        translate([0, 0, -plate_t]) linear_extrude(plate_t) difference() { plate2d(); holes2d(); }
        for (c = ["orange", "gold", "silver"])
            translate([0, 0, -color_t - eps]) linear_extrude(color_t + 2 * eps)
                if (c == "orange") orange2d(); else if (c == "gold") gold2d(); else silver2d();
        // 45 degree chamfer around the camera on the visible side
        translate([bx + cam_du, bv + cam_dv, -plate_t - eps])
            cylinder(d1 = cam_d, d2 = cam_d + 2 * plate_t, h = plate_t + 2 * eps);
    }
}

// ---------- body ----------

screw_pts = [
    for (s = [-1, 1]) [s * (hw_in(wall + 3.6) - 3.6), wall + 3.6],
    for (s = [-1, 1]) let(z = Hb - top_wall / cos(theta) - 6) [s * (hw_in(z) - 3.8), z]
];

module corner_blocks() {
    intersection() {
        outer_solid();
        for (p = screw_pts) {
            cx = sign(p[0]) * W / 2;
            cz = p[1] < Hb / 2 ? 0 : Hb;
            hull() {
                translate([p[0] - 4.5, D - 10, p[1] - 4.5]) cube([9, 10, 9]);
                // taper the front end at ~45 deg so it prints without support
                translate([(p[0] + cx) / 2, D - 19, (p[1] + cz) / 2]) cube(0.5, center = true);
                translate([cx, D - 19, cz]) cube(0.5, center = true);
            }
        }
    }
}

module body() {
    difference() {
        union() {
            difference() { outer_solid(); inner_void(); }
            corner_blocks();
        }
        // pocket for the face panel
        face_frame() translate([0, 0, -plate_t]) linear_extrude(plate_t + 1)
            offset(delta = plate_fit) plate2d();
        // camera hole and mic slots, through the face
        face_frame() translate([0, 0, -top_wall - 1]) linear_extrude(top_wall + 2) holes2d();
        // sled pin holes on the inside of the face
        face_frame() for (s = [-1, 1])
            translate([bx - board_w / 2 - fit - 1.5, bv + s * 6, -top_wall - eps]) cylinder(d = 2.2, h = 1.2);

        // USB-C opening through the right side wall
        face_frame() translate([bx + board_w / 2 - 2, bv - usb_open[0] / 2,
                                -top_wall - usb_depth - usb_open[1] / 2])
            cube([30, usb_open[0], usb_open[1]]);

        // screw pilots
        for (p = screw_pts) translate([p[0], D - 9, p[1]])
            rotate([-90, 0, 0]) cylinder(d = screw_pilot, h = 10);

        // recesses for 8 mm stick-on bumpers
        for (x = [-30, 30], y = [9, D - 9]) translate([x, y, -eps]) cylinder(d = 8.6, h = 0.8);
    }
}

// ---------- back plate ----------

module back_outline() {
    polygon([[-W / 2, 0], [W / 2, 0], [hw_out(Hb), Hb], [-hw_out(Hb), Hb]]);
}

module back_plate() {
    t = 2.4;
    difference() {
        translate([0, D + t, 0]) rotate([90, 0, 0]) linear_extrude(t) back_outline();
        for (p = screw_pts) translate([p[0], D - 1, p[1]]) rotate([-90, 0, 0]) {
            cylinder(d = screw_clear, h = t + 2);
            translate([0, 0, 1 + t - 1.4]) cylinder(d = 6.2, h = 2);
        }
        // vent slots
        for (i = [0 : 5]) translate([-18 + i * 7.2 - 1, D - 1, 22]) cube([2, t + 2, 16]);
        // registry, debossed
        translate([0, D + t - 0.6, 9]) rotate([0, 0, 180]) rotate([90, 0, 0])
            linear_extrude(1) text("NCC-1701-D", size = 4.2, font = "Liberation Sans:style=Bold",
                                   halign = "center", valign = "center");
    }
}

// ---------- board sled ----------
// Frame that the board's top edges press into. Print it as-is (pins up),
// then glue it to the inside of the face with the pins in their holes.

sled_h = 6;
module sled() {
    iw = board_w + 2 * fit; ih = board_h + 2 * fit;
    x0 = -iw / 2 - 3;        // thick wall on the side away from the USB end
    difference() {
        union() {
            translate([x0, -ih / 2 - 1.2, 0]) cube([3 + iw - 2.5, ih + 2.4, sled_h]);
            for (s = [-1, 1]) translate([x0 + 1.5, s * 6, sled_h - eps]) cylinder(d = 1.8, h = 1.0);
        }
        translate([-iw / 2, -ih / 2, -1]) cube([iw + 5, ih, sled_h + 2]);
    }
}

// ---------- reference shapes for the assembly view ----------

module board_dummy() {
    color("darkgreen") translate([-board_w / 2, -board_h / 2, -stack]) cube([board_w, board_h, stack - 4]);
    color("black") translate([cam_du, cam_dv, -4]) cylinder(d = 7.5, h = 4);
    color("silver") translate([board_w / 2 - 6.9, -4.5, -usb_depth - 1.6]) cube([7.5, 9, 3.2]);
}

// ---------- output ----------

// Panel parts share one print position, so they line up when loaded together.
module panel_print() translate([0, L / 2, 0]) rotate([180, 0, 0]) children();

c_black = "#1b1b1f"; c_orange = "#ff9c00"; c_gold = "#e8b923"; c_silver = "#c9ced6";

if (part == "assembly") {
    color(c_silver) body();
    color(c_silver) back_plate();
    face_frame() {
        color(c_black) panel_black();
        color(c_orange) panel_colour("orange");
        color(c_gold) panel_colour("gold");
        color(c_silver) panel_colour("silver");
        translate([bx, bv, -top_wall]) {
            color(c_silver) translate([0, 0, -sled_h]) sled();
            board_dummy();
        }
    }
} else if (part == "body") {
    translate([0, 0, D]) rotate([-90, 0, 0]) body();
} else if (part == "back") {
    translate([0, 0, D + 2.4]) rotate([-90, 0, 0]) back_plate();
} else if (part == "sled") {
    sled();
} else if (part == "panel_black") {
    panel_print() panel_black();
} else if (part == "panel_orange") {
    panel_print() panel_colour("orange");
} else if (part == "panel_gold") {
    panel_print() panel_colour("gold");
} else if (part == "panel_silver") {
    panel_print() panel_colour("silver");
}
