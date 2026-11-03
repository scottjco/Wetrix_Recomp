# 0.1.1

- Run **Wetrix.exe** directly on Windows, with no command script or console window. The executable also carries the reviewed HD Wetrix logo as its desktop and window icon.
- Missing or unsupported ROMs open a native file picker. A supported selection is verified and imported into `Assets/data.z64` for later launches. Cancelling exits cleanly.
- HD textures now ship inside every platform download, enabled by default for new profiles. The existing HD Textures switch still restores the original artwork.
- Redrew all ten red digital timer/counter digits at 16x native resolution. Corrected their texture bounds so replacements no longer depend on stale texture memory.
- Centred Practice's `1up` and `cpu` labels within their own views at widescreen and ultrawide ratios.
- Aligned both players' earthquake meters to their view's left edge, and beakers, arrows and previews to their view's right edge.
- Corrected the Practice CPU counter's complete panel, border and digits to use the right-edge inset, including its triangle-based drawing path.
- Updated Windows, Linux and both macOS release packages with licenses and bundled HD artwork. ROMs, saves and personal settings remain excluded.

# 0.1.0

First public preview of Wetrix Recompiled.

- Native N64 CPU and audio microcode recompilation with RT64 rendering.
- Hybrid, Interpolate and Original FPS modes; Display, 30, 60, 144, 240 and Unlimited targets.
- Original 4:3 and Expand layouts, including extended backgrounds, transitions and per-player HUD positioning.
- Keyboard, XInput and DualSense support, remappable controls and separate player device assignments.
- Optional HD texture pack distributed separately and enabled by default when installed.
- Persistent, automatically formatted Controller Pak; no shared save template.
- Windowed launch, automatic starting monitor and in-game settings without a launcher screen.
- Direct Windows executable launch without a console window; automatic ROM picker/import when the ROM is missing.
- Embedded desktop icon converted from the reviewed HD Wetrix logo.
- Practice labels centred per view at ultrawide ratios; both players' meters and previews aligned to their own view edges.
- Optional HD pack adds all ten red digital counter digits.
- Rainbow animation timing correction for Hybrid mode and missing PLAY corner texture replacement.

This is an early preview. Platform build success is distinct from gameplay testing.
