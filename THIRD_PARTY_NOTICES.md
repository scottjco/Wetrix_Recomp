# Third-party notices and license scope

Wetrix Recompiled integration changes are Copyright (c) 2026 Wetrix Recompiled contributors, licensed under GPL-3.0-or-later. The complete GPLv3 text is in `LICENSE`. This grant covers project-authored integration code and documentation, not third-party code or proprietary game material. Changes to dependencies remain subject to their upstream terms.

Original Wetrix code translated by the recompiler remains original-game code. Generated C is not represented as newly licensed game source. ROMs, extracted game data, music and original/derived artwork are outside this project's license grant. Requiring a locally supplied ROM and excluding ROM blobs does not itself establish redistribution permission for translated code or derived artwork. No clearance from the game's rights holders is claimed.

## Main dependencies

| Component | License / notice source |
| --- | --- |
| N64Recomp / RSPRecomp | MIT, `release-notices/upstream/lib/N64Recomp/LICENSE` |
| N64ModernRuntime | GPLv3, `release-notices/upstream/lib/N64ModernRuntime/COPYING` |
| RT64 | MIT, `release-notices/upstream/lib/rt64/LICENSE` |
| RecompFrontend | Current official upstream publishes GPLv3; see historical-pin note below |
| plume | MIT; its bundled Vulkan, D3D12 and Metal component notices are preserved |
| SDL2 | zlib license, supplied SDL2 COPYING text |
| FreeType | FreeType License selected; FTL, license overview and alternative GPLv2 text preserved |
| RmlUi | MIT; its container/debugger and Vulkan-backend notices are also preserved |
| LunaSVG / PlutoVG | Their respective MIT license texts |
| GamepadMotionHelpers / SlotMap | MIT; SlotMap's embedded notice preserved separately |
| Dear ImGui / ImPlot / im3d / hlslpp / ddspp | Their upstream license texts under `release-notices/upstream/` |
| nativefiledialog-extended | Its upstream license text |
| SPIRV-Cross / re-spirv | Their license texts; SPIRV-Cross LICENSES directory preserved |
| Vulkan Headers / volk / VulkanMemoryAllocator / D3D12MemoryAllocator / metal-cpp | Their bundled license and notice texts |
| stb / xxHash / zstd / miniz / concurrentqueue / nlohmann JSON / sse2neon | Standalone or embedded notices preserved |
| DirectX Shader Compiler and DXIL binaries | `release-notices/DXC-LICENSE.txt` and `DXC-ThirdPartyNotices.txt` |

This inventory includes build tools and conservative source-tree notices, not a claim that every listed component is linked into every platform binary. The current Windows configuration has the RmlUi HarfBuzz sample disabled, no MSDF target identified, and uses SDL rather than GLFW. A GLFW example notice is preserved conservatively. If another platform package adds HarfBuzz, MSDF, or additional runtime libraries, its packager must include their corresponding notices too. System-provided dependencies and shipped binary dependencies must be distinguished in the final archive inventory.

Exact checked dependency revisions, source paths and notice hashes are recorded in `release-notices/manifest.json`. Keep these notices and the matching source/dependency patches with binary releases. Notice collection alone is not a substitute for providing GPL Corresponding Source.

## RecompFrontend historical pin

The pinned checkout `b3b7ebb4ec1a8a763c0191486f1b3329f9499a48` contains no top-level COPYING/LICENSE. The official repository subsequently added GPLv3 in commit `2ddbfc8` ("Added GPL3 license (#49)"). Its current [COPYING](https://github.com/N64Recomp/RecompFrontend/blob/main/COPYING) is preserved as `release-notices/RecompFrontend-current-upstream-COPYING.txt`. This records the official project's published license rather than inventing a grant or pretending the old checkout contained that file. The integration is distributed under compatible GPLv3 terms. No upstream endorsement is implied.

## Interface assets and fonts

`Assets/menu/` contains the settings interface: Inter Variable, Noto Emoji, PromptFont, their notices, generic SVG control/navigation icons, and minimal CSS. Inspection found no Wetrix ROM-derived raster, music, ROM image or game texture there. These interface files are distinct from the bundled `Textures/` game artwork.

Inter: Copyright 2016 The Inter Project Authors. Noto Emoji: Copyright 2013 Google LLC. PromptFont by Yukari "Shinmera" Hafner, based on Xolonium by Severin Meyer: https://shinmera.com/promptfont . Font files retain their SIL Open Font License 1.1 texts both alongside the assets and in release notices. Font trademarks remain with their owners.

The twenty-two shipped SVG control/navigation and visual-mapping icons are newly authored geometric interface artwork by Wetrix N64 Recomp contributors, licensed under GPL-3.0-only. Their roles and SHA-256 hashes are recorded in `Assets/menu/icons/ATTRIBUTION.json`, with their license notice in `Assets/menu/icons/LICENSE.txt`. They replace the earlier copied reference icons; no license grant from the Silicon Valley project or an external icon author is asserted. Font licenses remain independent of the icon license.

## Bundled HD game artwork

Version 0.1.1 application archives include `Textures/hd-sprites/` with AI assistance disclosed and a separate artwork rights notice. Original/derived game artwork and trademarks are not relicensed by the application's GPL. A replacement being newly generated, high resolution, or AI-assisted does not establish rights in the original designs. The project makes no claim of permission from the original game's rights holders.

## Application icon

The embedded desktop icon in `resources/wetrix.ico` is converted from the reviewed AI-assisted HD Wetrix logo redraw. Its original game design and trademark remain with their rights holders. This small application-branding asset is distinct from the bundled gameplay textures and excluded from the application code GPL grant. See `resources/NOTICE.txt`.
