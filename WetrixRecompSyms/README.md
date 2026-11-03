# Wetrix metadata required

`boot-probe.syms.toml` now contains manually checked startup ranges for the
separate native diagnostic. See `docs/BOOT-RESULT.md`. A wider automatically
generated map is kept in `work/wetrix.draft.syms.toml` and is not validated.

No Wetrix ELF or symbol map was present in the supplied folder. The configured
`wetrix.us.syms.toml` deliberately does not exist yet: inventing function sizes
or treating the full ROM as executable code would produce invalid output.

Produce a map for the SHA-256 in the root README, with N64Recomp `[[section]]`
records containing `name`, `rom`, `vram`, `size`, and `functions` entries with
`name`, `vram`, and `size`. Identify code versus data, load addresses, function
boundaries, jump tables, relocations, and any overlays/compressed code first.
The ROM header entrypoint alone does not establish the complete load map.

Alternatively, produce a matching MIPS ELF with sized function symbols, and
adapt the configuration and project validator to the ELF input route.
SSSV symbols and patch addresses are not compatible with Wetrix.
