# Wetrix native runtime — current result

The Windows prototype runs Classic gameplay with keyboard/DualSense input,
audio synthesis, and a persistent 32 KiB controller pak. N64Recomp translates
CPU code from the verified Wetrix ROM, N64ModernRuntime supplies scheduling,
and RT64 provides rendering. The ROM remains unchanged and ignored by Git.

Escape opens the shared RecompFrontend settings menu used by Silicon Valley;
Wetrix starts directly without a launcher screen. Settings persist in
config/user. See CONTROLS-AND-MENU.md for controls and available settings.

Game logic is paced at 30 FPS. VI/audio processing remains 60 Hz. RT64 generates
interpolated frames up to the selected display/manual target (maximum 240).
The title measures rendered frames; logs separately measure game and render rates.

Verified: Release build, visible Classic board, working user-confirmed menu,
controller pak persistence, and interpolated rendering at roughly 60 and 240 FPS
in lighter scenes. The water matching optimization subsequently held approximately
30 FPS gameplay and 240 FPS rendering with filled audio buffers; the user confirmed
the slowdown appeared resolved. See TIMING-AND-CLASSIC.md for measurements.
The boot diagnostic previously passed 42 checks; the pak persistence test passed.

Limitations: complete gameplay and every mode are not validated. XInput is
implemented but not hardware-tested. No original ELF or symbol map was supplied;
the runtime uses an experimentally recovered function map.
