# Changelog

## 3.0.0 — 2026-10-08

- Add a mandatory full-height asymmetric key before every version 3 ID. The key provides a viewing-face cue for symmetric codes such as H3 and I3.
- Default new IDs to 5 mm cap height. Preserve all version 2 character geometry and stencil bridges.
- Group the key and character paths together. Add exact and fitted-polyline Python exports and separate AutoCAD version 3 commands.
- Add front/back and rotation regressions, reopened-DXF checks, full character previews and a 1:1 printable specimen.
- Keep the version 2 files for historical reproduction. Existing drawings and cutting packages are not rewritten.

Version 3 includes Python/DXF regressions and bounded native AutoCAD Core Console 2023 checks. Actual CAM import and physical cutting/readability remain unverified for this revision; the CAD notes identify the native paths tested.
