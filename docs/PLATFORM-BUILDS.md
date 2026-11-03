# Platform builds

Version 0.1.0 has build targets for Windows x64, Linux x64, macOS Apple Silicon and macOS Intel. Windows is the locally playtested platform. All four platforms passed native compilation, the Pak persistence/controller-protocol test and packaging in [the release build run](https://github.com/scottjco/Wetrix_Recomp/actions/runs/41551884023). Compilation alone does not establish gameplay parity.

## ROM-free release builds

```
git submodule update --init --recursive
python tools/ci_release.py prepare
cmake -S . -B build-release -G Ninja -DCMAKE_BUILD_TYPE=Release -DWETRIX_USE_PREGENERATED=ON
cmake --build build-release --target WetrixRuntime WetrixPakTest --parallel 3
```

The verified `generated/recompiled-source.tar.gz` contains translated C/C++ and headers only. It contains no ROM image, texture bank or game-data blob. Regenerating those sources requires a locally supplied supported ROM. Native game assets are loaded from that ROM at runtime.

The release workflow installs platform dependencies and builds on native Windows, Ubuntu and macOS runners. Windows uses D3D12, Linux uses Vulkan, and macOS uses RT64's Metal backend. Linux requires SDL2, GTK3, FreeType and a suitable Vulkan driver. macOS packages target macOS 15 or newer, bundle their Homebrew library dependencies and are ad-hoc signed, not notarized. Linux packages are built on Ubuntu 24.04.

Use `Run Wetrix.cmd` on Windows, `Run Wetrix.sh` on Linux, or `Run Wetrix.command` on macOS. Place your supported ROM at `Assets/data.z64` relative to that launcher. Extract into a writable folder because preferences and saves are portable.

Application archives exclude ROMs, the optional HD texture pack, saves and personal settings. The HD pack is a separate ZIP that extracts a `Textures/hd-sprites/` directory beside the application. Removing it hides the HD setting; a new installation with the pack defaults to HD On.

Full licensing texts and corresponding project source/patches accompany the public release. See the repository's Actions and Releases pages for actual build results and available downloads.
