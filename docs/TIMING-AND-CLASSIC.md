# Timing and Classic compatibility

Graphics completion is released every second 60 Hz retrace: gameplay runs at
30 FPS while the original audio thread still receives 60 retraces per second.
Reducing the entire retrace clock to 30 Hz starved the 22050 Hz audio device.
SDL audio feedback reserves two retraces (33 ms) of PCM to accommodate device
block consumption and scheduling jitter. No sample-rate or pitch change is used.
The ten-second audio log reports production rate, pending milliseconds, and
empty queues observed immediately before submitting PCM (including startup).

Classic's audio-stop spin loops now yield to host scheduling. Once these loops
complete, the original game creates empty border display lists whose unused
vertex pointer is overwritten by a terrain colour. RT64 previously read outside
the host's 8 MiB allocation and crashed. The bounded vertex read supplies zeros
for absent RAM, without mirroring it or skipping valid terrain drawing. See
[ares RDRAM read implementation](https://github.com/ares-emulator/ares/blob/master/ares/n64/rdram/rdram.hpp).
The tracked patch in patches/rt64-rdram-vertices.patch is applied idempotently
during CMake configuration. Unknown/conflicting source versions fail configuration.

Verified: Release build, visible Classic terrain, and approximately 30 FPS.
Long gameplay sessions, all modes, and audible output quality still need testing.

## Interpolation and water performance

Game tasks supply RT64 with a 30 FPS source rate. Display or Manual framerate
settings generate intermediate frames without increasing gameplay or audio speed.
Manual targets extend to 240 FPS, capped by the monitor's refresh rate. The title
counts rendering hooks; logs independently report game and rendering rates.
Presentation uses PresentEarly, matching the Silicon Valley reference.

Water exposed a quadratic search in RT64's automatic frame matching. Repeated
draw calls with the same hash, matrix range, tile indices, and look-at index
contributed duplicate combinations to the same candidate sets. The local patch
deduplicates those matching inputs before the Cartesian product. Geometry,
water simulation, and interpolation remain enabled.

Observed on the RTX 5090 test machine: matching fell from roughly 25–31 ms to
0.13–0.34 ms. Water gameplay held approximately 30 FPS with 240 FPS rendering;
audio sustained approximately 22050 stereo frames/sec with no empty queues
after startup. The user confirmed the water slowdown appeared resolved.
These observations are not a guarantee for all scenes or hardware.

The renderer changes and periodic timing diagnostics are all preserved in
patches/rt64-rdram-vertices.patch and reapplied by tools/patch_rt64.py at configure
time. RecompFrontend is pinned to the same upstream revision as Silicon Valley;
tools/prepare_frontend.py builds its in-game UI without the launcher/mod browser.
