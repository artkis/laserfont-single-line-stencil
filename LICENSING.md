# Licensing

Copyright (c) 2026 Artkis.

This distribution contains font software and general utility code under separate licenses. There are no Reserved Font Names.

## Font software (SIL Open Font License 1.1)

The following original font components are licensed under [OFL.txt](OFL.txt):

- The LaserFont and laserfont2 glyph designs, including Bézier controls, stroke geometry, bridge placements, advance widths and derived arc geometry.
- `glyphs-v2.json`, `glyphs-v2-polyline.json`, compiled glyph tables, `laserfont2.shp` and `laserfont2.shx`.
- The version 3 orientation-key design, `orientation-key.json`, and its embedded coordinates in `LASER3.lsp`.
- The version 3 display font source `cad/laserfont3.shp` and compiled `cad/laserfont3.shx`, including the reserved orientation-key prefix glyph.
- `build_glyphs.py`, which is the original, executable glyph-design source.
- The embedded glyph tables in generated AutoLISP files. The tables retain their OFL license when packaged together with the MIT runtime.
- Font specimen masters and collections that distribute the glyph set as reusable font geometry.

Converting a font to another representation does not change the license of that font data. Keep the copyright notice and OFL text when distributing these font components or modified versions. The OFL itself explains its conditions; its application to Font Software does not place documents created using the font under the OFL.

## Utility code and documentation (MIT)

General rendering, transformation, DXF export, approximation, validation and AutoLISP command/runtime code is licensed under [LICENSE-MIT.txt](LICENSE-MIT.txt), except for the font components specifically listed above. This includes the utility portions of generated files containing both runtime code and glyph tables.

The version 3 installer `cad/Install-LaserFont3.ps1`, its generated loader, `cad/integration3.lsp`, and the utility code in `cad/build_display3.py` also use the MIT License. Generated SHP/SHX font data remain under the OFL.

The project README and general utility documentation are also MIT-licensed. This does not relicense the font data described in those documents, the OFL text, or any linked third-party material.

## Combined files

A generated `LASER2.lsp` or `LASER3.lsp` contains both OFL font tables and MIT utility code. Distribute both license files with it. The presence of MIT runtime code does not grant permission to distribute the font tables under MIT; the presence of OFL font tables does not relicense unrelated utility code under OFL.

## Dependencies and references

Python, ezdxf, Pillow and any other optional tools retain their own licenses. References to AutoCAD, CypCut, Friendess or other products identify interoperability targets or technical sources; they do not imply sponsorship or endorsement.

Official license sources: [SIL Open Font License 1.1](https://openfontlicense.org/open-font-license-official-text/) and [MIT License](https://opensource.org/license/mit).
