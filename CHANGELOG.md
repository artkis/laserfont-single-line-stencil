# Changelog

## 3.0.4 — 2026-10-09

- Make AutoCAD `LASEROUT` output separate open polylines without creating a drawing group. No manual `UNGROUP` step is needed.
- Preserve the arrow geometry, glyphs, default height 5, existing text heights and conversion Undo. The Python DXF exporter retains its grouped output.

## 3.0.3 — 2026-10-09

- Replace the corner symbol with a simple upward arrow before the ID. It points toward the top of the readable lettering and follows the label's rotation; it does not indicate global assembly up.
- Use two open paths, a stem and a chevron, to form one arrow without a closed hole. At height 5 it measures 5 by 3 mm, with a 1.5 mm gap before the code and the same 4.5 mm added label width.
- Use the arrow's position before the ID and its direction together as the orientation cue. A plain arrow alone has mirror symmetry.
- Preserve the original glyphs, one `LASEROUT` conversion command, `LASERFONT` setup, default height 5 and existing text heights. Bare IDs and one existing `~` prefix remain accepted, producing one arrow grouped with the ID.
- Load the combined runtime once from the installed loader; its integration commands are already embedded.

## 3.0.2 — 2026-10-09

- Use one AutoCAD conversion command, `LASEROUT`, with `LASERFONT` for style setup. Remove the numbered conversion, insertion and polyline aliases from the current command interface and installer registration.
- Accept ordinary bare IDs in LaserFont3 TEXT and plain one-line MTEXT. `LASEROUT` adds exactly one orientation key automatically. Existing text with one leading `~` is also accepted; doubled or embedded prefixes remain invalid.
- Keep the new-text default at 5 drawing units and preserve each selected label's existing height during conversion, including 2.5-unit labels.
- Retain fitted open arc/line polyline output, original text positioning and grouped key-plus-ID geometry. Keep the previous source files as historical references.

## 3.0.1 — 2026-10-08

- Add the compiled `laserfont3.shx` display font and its SHP source. A reserved leading `~` displays the orientation key once per ID.
- Add `LASERFONT` to select the editable style at height 5 and `LASERTEXT3` to create an editable keyed ID. New geometry still defaults to height 5; conversion retains the source text's height.
- Accept eligible `laserfont`, `laserfont2` and `laserfont3` text. Preserve legacy character baselines and version 3 key baselines. Reject missing, duplicated or embedded version 3 key prefixes.
- Route familiar commands to keyed version 3 output. `LASEROUT` keeps polyline output, matching the original installed converter's output type; `LASEROUT2` and `LASEROUT3` produce exact Bézier/line geometry. `LASER2`, `LASERPOLY2` and `LASERPOLY` also use the keyed commands. Preserve the historical version 2 files.
- Add a Windows AutoCAD 2023 installer with verified backups, existing ProductCode retention and installed-file hash checks. Preserve legacy SHX files and leave drawing files, registry security settings and the Startup Suite unchanged.
- Pass 41 of 41 isolated AutoCAD Core Console checks, including the compiled font, editable text, compatibility aliases, cancellation and one-step Undo. Reopen the saved DWG with all 20 entities and four groups intact.
- Resolve the earlier partial Undo test result by correcting automatic script-level grouping in the test harness. The delivered routines do not change the user's Undo settings; their runtime Begin/End logic did not require a repair.

The native report records the tested scope. GUI installation and foreground use, actual CAM import, physical cutting and human recognition remain outside that isolated test suite.

## 3.0.0 — 2026-10-08

- Add a mandatory full-height asymmetric key before every version 3 ID. The key provides a viewing-face cue for symmetric codes such as H3 and I3.
- Default new IDs to 5 mm cap height. Preserve all version 2 character geometry and stencil bridges.
- Group the key and character paths together. Add exact and fitted-polyline Python exports and separate AutoCAD version 3 commands.
- Add front/back and rotation regressions, reopened-DXF checks, full character previews and a 1:1 printable specimen.
- Keep the version 2 files for historical reproduction. Existing drawings and cutting packages are not rewritten.

Version 3 includes Python/DXF regressions and bounded native AutoCAD Core Console 2023 checks. Actual CAM import and physical cutting/readability remain unverified for this revision; the CAD notes identify the native paths tested.
