# Release notice collection

Include this directory, the root LICENSE and THIRD_PARTY_NOTICES.md with the application release. `manifest.json` records the pinned dependency revisions and local notice sources. `upstream/` preserves license texts in their source-directory layout. Embedded notices are copied verbatim from source headers or comment blocks.

DXC notices came from the inspected Silicon Valley release reference and apply to the DirectX Shader Compiler family shipped by the RT64 tool dependency. They are retained in full, not used as a grant for unrelated binaries. The release packager must retain an exact binary inventory and its associated notices.

The current official RecompFrontend GPLv3 COPYING was checked against its official repository; the older pinned checkout predates that file. The twenty-two shipped generic SVG interface icons are newly authored GPL-3.0-only project artwork, with their own license and hash attribution copied into this collection. See THIRD_PARTY_NOTICES.md for scope and font attribution.

No ROM or optional HD game-art files belong in the base application archive. Generated translated game code remains subject to original rights; these notices do not claim clearance. Publish the exact corresponding integration source, dependency revisions, patches and build scripts for the binary version.
