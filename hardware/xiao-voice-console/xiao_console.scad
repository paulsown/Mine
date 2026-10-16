// Starfleet desk console for a Seeed XIAO ESP32S3 Sense (Home Assistant voice satellite)
//
// Sloped LCARS-style front face, combadge inlay, camera window, mic grille,
// and a USB-C power opening on the right side.
//
// Parts (set `part` or use -D part="\"body\"" on the command line):
//   assembly     everything in place, for looking at
//   body         main shell, already rotated to print on its open back
//   back         back plate (vents, screw holes)
//   sled         board holder, glued to the inside of the face
//   badge_oval   combadge oval inlay (print in gold/yellow)
//   badge_delta  combadge delta inlay (print in silver/grey)
//
// All sizes in mm. Check the "board" and "usb" values against your own board
// before printing; they are the ones most likely to need a nudge.

part = "assembly";

/* [Case] */
W    = 84;     // width at the floor
D    = 64;     // depth front to back
Hf   = 16;     // height of the front edge
Hb   = 48;     // height of the back edge
wall = 2.4;
taper = 0.10;  // side walls lean in this much per mm of height

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
function face_y(v, d = 0) = v * cos(theta) + d * sin(theta);
// half-width of the face itself
function face_hw(v) = hw_out(face_z(v));

// Board placement: USB-C end sits `board_gap` short of the inner side wall
// at the board's highest corner.
board_top_z = face_z(board_v + board_h / 2, wall);
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
    dz = wall / cos(theta);
    y0 = wall; y1 = D + 1;
    wedge(W / 2 - wall * side_k, y0, y1, wall,
          Hf + y0 * tan(theta) - dz, Hf + y1 * tan(theta) - dz);
}

// Local frame on the face: x = across, y = up the slope, z = out of the face.
module face_frame() translate([0, 0, Hf]) rotate([theta, 0, 0]) children();

// ---------- 2D artwork ----------

function bez(p0, p1, p2, n = 12) =
    [for (i = [0 : n]) let(t = i / n)
        (1 - t) * (1 - t) * p0 + 2 * (1 - t) * t * p1 + t * t * p2];

module delta2d() {
    // TNG combadge arrowhead, 22 wide x 30 tall, origin at its middle
    pts = concat(
        bez([0, 16], [7, 3], [11, -14]),     // right edge
        bez([11, -14], [5, -9], [0, -6]),    // notch, right half
        bez([0, -6], [-5, -9], [-11, -14]),  // notch, left half
        bez([-11, -14], [-7, 3], [0, 16])    // left edge
    );
    polygon(pts);
}

module oval2d() translate([0, -2]) scale([16, 8.5]) circle(1);

module badge2d() union() { oval2d(); delta2d(); }

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

// Raised LCARS panels on the face (all in face coordinates)
module lcars2d() {
    lx  = -face_hw(66) + 4;          // left margin at the top of the face
    top = 66;
    // elbow + upper part of the left bar
    elbow2d(lx, 22, 4, top, 9, 6, 9, 4);
    // lower block of the left bar
    translate([lx, 6]) square([9, 14.5]);
    // top bar segments
    translate([5.5, top - 6]) square([15, 6]);
    pill(22, top - 6, face_hw(top) - 4, top);
    // bottom rail
    translate([lx + 11, 4]) square([31, 3]);
    // stacked buttons, lower right
    for (i = [0 : 2]) pill(18 - i * 3, 5 + i * 7, face_hw(24) - 4, 10 + i * 7);
}

module mic_slots2d() {
    for (s = [-1, 1]) for (i = [0 : 2])
        translate([bx + cam_du + s * (5.4 + i * 2.2) - 0.6, bv - 6]) square([1.2, 12]);
}

// ---------- body ----------

screw_pts = [
    for (s = [-1, 1]) [s * (hw_in(wall + 3.6) - 3.6), wall + 3.6],
    for (s = [-1, 1]) let(z = Hb - wall / cos(theta) - 6) [s * (hw_in(z) - 3.8), z]
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
            // raised LCARS artwork
            intersection() {
                face_frame() translate([0, 0, -eps]) linear_extrude(0.8 + eps) lcars2d();
                // keep it on the face
                face_frame() translate([-W, 0, -1]) cube([2 * W, L, 3]);
            }
        }
        // combadge pocket
        face_frame() translate([-6, 26, -1.2]) linear_extrude(2) badge2d();

        // sensor window: shallow recess around camera and mic slots
        face_frame() translate([0, 0, -0.6]) linear_extrude(2)
            rrect(bx - 12, bv - 11, min(bx + 11.5, face_hw(bv + 11) - 2), bv + 11, 3);
        // camera hole with outer chamfer
        face_frame() translate([bx + cam_du, bv + cam_dv, 0]) {
            translate([0, 0, -wall - 1]) cylinder(d = cam_d, h = wall + 3);
            translate([0, 0, -1.8]) cylinder(d1 = cam_d, d2 = cam_d + 4, h = 2);
        }
        // mic grille
        face_frame() translate([0, 0, -wall - 1]) linear_extrude(wall + 3) mic_slots2d();
        // sled pin holes on the inside of the face
        face_frame() for (s = [-1, 1])
            translate([bx - board_w / 2 - fit - 1.5, bv + s * 6, -wall - eps]) cylinder(d = 2.2, h = 1.4);

        // USB-C opening through the right side wall
        face_frame() translate([bx + board_w / 2 - 2, bv - usb_open[0] / 2,
                                -wall - usb_depth - usb_open[1] / 2])
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
            for (s = [-1, 1]) translate([x0 + 1.5, s * 6, sled_h - eps]) cylinder(d = 1.8, h = 1.2);
        }
        translate([-iw / 2, -ih / 2, -1]) cube([iw + 5, ih, sled_h + 2]);
    }
}

// ---------- combadge inlays ----------

module badge_oval() linear_extrude(1.2) offset(delta = -0.15) difference() { oval2d(); offset(delta = 0.15) delta2d(); }
module badge_delta() linear_extrude(2.2) offset(delta = -0.15) delta2d();

// ---------- reference shapes for the assembly view ----------

module board_dummy() {
    color("darkgreen") translate([-board_w / 2, -board_h / 2, -stack]) cube([board_w, board_h, stack - 4]);
    color("black") translate([cam_du, cam_dv, -4]) cylinder(d = 7.5, h = 4);
    color("silver") translate([board_w / 2 - 6.9, -4.5, -usb_depth - 1.6]) cube([7.5, 9, 3.2]);
}

// ---------- output ----------

if (part == "assembly") {
    color("gainsboro") body();
    color("gainsboro") back_plate();
    // paint suggestion for the raised LCARS panels
    color("#f2a65a") face_frame() linear_extrude(0.85) lcars2d();
    face_frame() translate([bx, bv, -wall]) {
        color("orange") translate([0, 0, -sled_h]) sled();
        board_dummy();
    }
    face_frame() translate([-6, 26, -1.2]) {
        color("gold") badge_oval();
        color("silver") badge_delta();
    }
} else if (part == "body") {
    translate([0, 0, D]) rotate([-90, 0, 0]) body();
} else if (part == "back") {
    translate([0, 0, D + 2.4]) rotate([-90, 0, 0]) back_plate();
} else if (part == "sled") {
    sled();
} else if (part == "badge_oval") {
    badge_oval();
} else if (part == "badge_delta") {
    badge_delta();
}
