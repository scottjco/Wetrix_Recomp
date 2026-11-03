# Future game patches

Only add hooks after identifying their Wetrix function names and addresses.
Review DMA/overlay loading, OS/library replacements, and hardware accesses.
No SSSV patches have been copied.

rt64-rdram-vertices.patch contains the local RT64 compatibility changes:
bounded reads for absent terrain-border vertex memory, duplicate draw-call
matching elimination for water interpolation, and periodic renderer timing logs.
tools/patch_rt64.py applies it idempotently during CMake configuration.

Widescreen background work uses tagged RDP no-op commands (C0575458) emitted
around Wetrix's background dispatcher (8001E6F8) and decorative menu circles
(800278A8). Layer 1 extends only backdrop drawing and clipping; layer 2 preserves
whole circles through the game's CPU clip and spreads their travel across the
window at unchanged sprite size. Foreground geometry is not tagged. The marker
is consumed in RT64's RDP no-op handler and flushed at layer boundaries.

The native 16px/8px TV masks are omitted, and menu fill strips cover the window.
Practice backdrop and bottom-edge coverage still require visual confirmation in
the rebuilt version. Timing remains 30 gameplay updates/s with higher rendered
FPS through interpolation; actual 60 Hz gameplay/input work is not implemented.

The tagged gameplay backdrop also extends the producer's written color bounds
from 232 to 240 rows before framebuffer submission. RT64 derives targetHeight
from those bounds; changing only the render scissor leaves the final eight rows
unrendered and exposes old menu pixels. A one-time startup log records activation.

Full-width pause/transition panels and Score Codes gradient strips now use the
window width, preserving alpha, colours and partial-height gradient placement.
Untextured screen-plane quads are recognized by their original 0..320 or
16..304 horizontal bounds with depth disabled; foreground meshes are excluded.

frontend-two-player.patch adds two player tabs and device selection to the shared
Controls page. Device assignments live in config/user/player_devices.json;
bindings stay in controls.json. Player 1 retains the existing single-player
profiles, while Player 2 has independent keyboard/controller profiles. Keyboard
Player 2 defaults: IJKL, U drop, O rotate, right Shift start. Both virtual N64
ports are present so Multiplay is available; unassigned devices send neutral input.
The pak remains on port 1, with port 2 reporting a controller without an accessory.
Explicit device identities reconnect by SDL GUID/serial and duplicate ordinal;
identical controllers without serials may require reselection if their order changes.
