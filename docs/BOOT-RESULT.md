# First native execution result — 2026-11-02

`WetrixBootProbe.exe` executes five original ROM routines translated by
N64Recomp and compiled with MSVC for Windows x64. This is a bounded diagnostic,
not a playable Wetrix port. All 42 checks passed.

| Verified native routine | RAM address | ROM range (end exclusive) |
| --- | --- | --- |
| Entry / BSS clear | `80000400` | `1000–103C` |
| Game main | `80031DC0` | `329C0–32AB4` |
| Create thread | `800503C0` | `50FC0–51104` |
| Disable interrupts | `80051540` | `52140–52160` |
| Restore interrupts | `80051560` | `52160–5217C` |

The diagnostic seeds RAM with nonzero bytes, loads the ROM's initial payload
using the recompiler's word-swapped RAM layout, and calls the translated
entrypoint. It verifies the entire 720,064-byte BSS range
`8007C380–8012C040` is zero, with sentinels immediately outside preserved.
The original main then selects its clock using the boot TV-type word:

| Injected TV type | Clock written by original main |
| --- | --- |
| 0 (PAL) | 49,656,530 Hz |
| 1 (NTSC) | 48,681,812 Hz |
| 2 (MPAL) | 48,628,316 Hz |

These are three inputs to the same supplied US ROM, not tests of three ROM
releases. The translated thread-creation function writes thread ID 1,
priority 10, entry `80031EB4`, and stack pointer `8006FAB0`, propagates the
input argument, links the thread into its list, and restores interrupt status.

## Explicit diagnostic boundaries

- The call at `80051240` is identified as OS initialization from its startup
  role and inspected code. The diagnostic checks state there, then returns
  without executing hardware initialization. It does not claim that OS
  initialization worked.
- CP0 Status reads/writes use a diagnostic host register, with no interrupts
  delivered.
- The start-thread call at `8005C100` validates the context and ends the test.
  There is no scheduler, thread execution, renderer, audio, or gameplay.
- Neither ignored boundary has a silent empty stub: both run assertions and
  are explicitly named `probe_*` in the separate diagnostic configuration.

## Reproduce

From `C:\recomp\wetrix_n64`:

```powershell
cmake --preset windows
cmake --build --preset boot-probe --parallel 8
```

Or double-click `Run Boot Probe.cmd` after building. The launcher checks the
complete ROM SHA-256 before executing. The executable's own file check is
only size/byte-order; use the hash-checking launcher or CMake target.

## Broader ROM analysis

The public [queueRAM Wetrix analysis](https://github.com/queueRAM/wetrix),
commit `dab3d24400972833dce21dd4ac01a14102cea6c4`, specifies the exact same
SHA-1 as the supplied ROM. Its existing segment split is incomplete and
misclassifies RSP bytes as main CPU code; it was used only as a reference.

Direct inspection found CPU code starting at ROM `10DC0`, following RSP code,
and ending at `648FC`, followed by data. The main CPU scan with spimdisasm
1.42.4 / rabbitizer 1.16.2 yielded 992 candidate routines plus the boot entry.
This is a draft, not 993 verified functions. In particular, unused padding
contains old instruction fragments that confuse automatic boundary detection.
The initial scan incorrectly placed main at `80031DAC`; the boot JAL and
control-flow inspection establish its actual entry at `80031DC0`.

An experimental full translation stopped at `func_80011100`, whose debug
exception path writes CP0 ErrorEPC (register 30), unsupported by this
N64Recomp version. This routine must be classified and handled deliberately,
not patched to do nothing. The broader map remains under `work/`, separate
from the verified diagnostic map.

Re-run analysis with:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tools/requirements-analysis.txt
.\.venv\Scripts\python.exe tools/analyze.py
```

This writes draft metadata, disassembly, and context tables under `work/`.
The ROM also contains the literal F3DEX.NoN 1.21 graphics microcode signature
at ROM `64BB0`; exact microcode task ranges and runtime compatibility still
need validation.

Next: correct the wider function map and identify OS/library boundaries,
then integrate scheduling, PI/DMA, VI, controller/save handling, and the
graphics/audio runtime. The normal full-game `recompile` target remains
guarded until a validated whole-game symbol map is supplied.
