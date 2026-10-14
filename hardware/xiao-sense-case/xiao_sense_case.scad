// Case for Seeed Studio XIAO ESP32S3 Sense (base board + camera/mic expansion board)
// Two parts: a base tray and a press-fit lid. Print both flat side down, no supports.
//
// Board: 21 x 17.8 mm, ~15 mm tall with the Sense board and camera stacked.
// Measure your board with calipers and adjust the values below if needed.

part = "both";          // "base", "lid" or "both"

/* [Board] */
board_l    = 21.0;      // along the USB-C axis
board_w    = 17.8;
pcb_t      = 1.2;
stack_h    = 15.0;      // bottom of base PCB to top of camera
clearance  = 0.5;       // gap around the board on each side

/* [Case] */
wall       = 1.6;
floor_t    = 1.6;
lid_t      = 1.6;
corner_r   = 2.5;
ledge_h    = 1.5;       // board rests on rails this high off the floor (keeps bottom pads clear)
ledge_w    = 1.0;
lip_h      = 3.0;       // depth of the lid's press-fit lip
lip_t      = 1.2;
fit        = 0.2;       // lip clearance; raise to 0.3 if the lid is too tight

/* [Openings] */
usb_w      = 12.5;      // sized for a cable plug's overmold, not just the receptacle
usb_h      = 7.0;
cam_d      = 9.0;
cam_dx     = 0;         // camera hole offset from lid center (+x = away from USB)
cam_dy     = 0;
slot_w     = 1.2;
slot_len   = 6.0;
slot_pitch = 2.8;
lid_grille = true;

$fn = 48;

in_l = board_l + 2*clearance;
in_w = board_w + 2*clearance;
in_h = ledge_h + stack_h + 1.0;
out_l = in_l + 2*wall;
out_w = in_w + 2*wall;
out_h = floor_t + in_h;

module rbox(l, w, h, r) {
    hull() for (x = [r, l-r], y = [r, w-r]) translate([x, y, 0]) cylinder(r=r, h=h);
}

module slot_row(n, len, vertical=true) {
    for (i = [0:n-1]) translate([(i - (n-1)/2) * slot_pitch, 0, 0])
        hull() for (d = [-(len-slot_w)/2, (len-slot_w)/2])
            translate(vertical ? [0, 0, d] : [0, d, 0])
                rotate(vertical ? [90, 0, 0] : [0, 0, 0]) cylinder(d=slot_w, h=10, center=true);
}

module base() {
    usb_z = floor_t + ledge_h + pcb_t + 1.6;    // USB-C receptacle centerline
    grille_z = floor_t + ledge_h + stack_h*0.6; // around the expansion board (mic level)
    difference() {
        rbox(out_l, out_w, out_h, corner_r);
        // cavity
        translate([wall, wall, floor_t]) rbox(in_l, in_w, in_h + 1, max(corner_r - wall, 0.5));
        // USB-C opening
        translate([0, out_w/2, usb_z]) rotate([0, 90, 0])
            hull() for (dz = [-(usb_w-usb_h)/2, (usb_w-usb_h)/2])
                translate([0, dz, 0]) cylinder(d=usb_h, h=wall*3, center=true);
        // mic / vent slots on both long walls
        for (y = [wall/2, out_w - wall/2]) translate([out_l/2, y, grille_z]) slot_row(5, slot_len);
        // slots on the far end wall
        translate([out_l - wall/2, out_w/2, grille_z]) rotate([0, 0, 90]) slot_row(4, slot_len);
    }
    // support rails along the long sides
    for (y = [wall, out_w - wall - ledge_w])
        translate([wall + 1.5, y, floor_t - 0.01]) cube([in_l - 3, ledge_w, ledge_h]);
}

module lid() {
    il = in_l - 2*fit;
    iw = in_w - 2*fit;
    difference() {
        union() {
            rbox(out_l, out_w, lid_t, corner_r);
            // press-fit lip
            translate([wall + fit, wall + fit, lid_t - 0.01]) difference() {
                rbox(il, iw, lip_h, max(corner_r - wall, 0.5));
                translate([lip_t, lip_t, -1]) rbox(il - 2*lip_t, iw - 2*lip_t, lip_h + 2, 0.5);
            }
        }
        // camera hole (lid prints upside down, so mirror y to keep it over the lens)
        translate([out_l/2 + cam_dx, out_w/2 - cam_dy, -1]) cylinder(d=cam_d, h=lid_t + 2);
        // two slots between the camera and the far end
        if (lid_grille)
            translate([out_l - wall - fit - lip_t - 2.4, out_w/2, lid_t/2]) slot_row(2, 7, false);
    }
}

if (part == "base") base();
else if (part == "lid") lid();
else { base(); translate([0, out_w + 6, 0]) lid(); }
