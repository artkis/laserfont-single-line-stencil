# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Artkis
"""Render the saved version 3 DXF samples, including front/back comparisons."""
from pathlib import Path
import math
import ezdxf
from ezdxf import path
from PIL import Image, ImageDraw
import generate_laserfont2 as v2
import generate_laserfont3 as v3

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "examples"


def groups(filename):
    doc = ezdxf.readfile(filename)
    return [[[(p.x, p.y) for p in path.make_path(e).flattening(.001)]
             for e in g] for _, g in doc.groups]


def draw_paths(draw, curves, box, color, flip=None, width=5):
    pts = [p for c in curves for p in c]
    cx = (min(p[0] for p in pts)+max(p[0] for p in pts))/2
    cy = (min(p[1] for p in pts)+max(p[1] for p in pts))/2
    sx = -1 if flip in ("back-x", "upside-down") else 1
    sy = -1 if flip in ("back-y", "upside-down") else 1
    dx = max(p[0] for p in pts)-min(p[0] for p in pts)
    dy = max(p[1] for p in pts)-min(p[1] for p in pts)
    scale = min((box[2]-box[0])/dx, (box[3]-box[1])/dy)
    mx, my = (box[0]+box[2])/2, (box[1]+box[3])/2
    for c in curves:
        draw.line([(mx+(x-cx)*sx*scale, my-(y-cy)*sy*scale) for x, y in c],
                  fill=color, width=width, joint="curve")


def preview():
    OUT.mkdir(exist_ok=True)
    v3.build_samples(OUT)
    saved = groups(OUT / "laserfont3-H5-samples-bezier.dxf")
    image = Image.new("RGB", (1800, 1110), "#f6f4ee")
    d = ImageDraw.Draw(image)
    d.text((55, 32), "LaserFont 3 | Outside-face ID", fill="#182b32", font=v2.font(48))
    d.text((55, 96), "5 mm lettering and arrow  /  9 October 2026", fill="#496069", font=v2.font(25))
    titles = [("OUTSIDE / CORRECT", None), ("BACK / LEFT-RIGHT FLIP", "back-x"),
              ("BACK / TOP-BOTTOM FLIP", "back-y"), ("FRONT / UPSIDE DOWN", "upside-down")]
    for col, (title, flip) in enumerate(titles):
        left = 40+col*440
        color = "#067047" if col == 0 else "#9f3b22"
        d.rounded_rectangle((left, 158, left+420, 754), 12, fill="white", outline="#dddcd5", width=2)
        d.text((left+18, 177), title, fill=color, font=v2.font(19))
        for row, curves in enumerate(saved[:2]):
            top = 243+row*245
            draw_paths(d, curves, (left+32, top, left+386, top+155), color, flip)
            d.text((left+18, top+177), "H3" if row == 0 else "I3", fill="#4f6268", font=v2.font(22))
    d.text((55, 792), "Read the WHOLE mark: arrow + ID", fill="#182b32", font=v2.font(33))
    d.text((55, 842), "Arrow BEFORE the ID, pointing toward the TOP of the readable lettering.", fill="#182b32", font=v2.font(27))
    d.text((55, 889), "Two open arrow paths. No closed extra hole. The panel code stays unchanged.", fill="#496069", font=v2.font(24))
    d.text((55, 951), "Front/back views are rendered from the saved DXF at equal scale; enlarged for inspection.", fill="#496069", font=v2.font(21))
    d.text((55, 988), "Place the complete label on the final OUTSIDE reading face. The arrow is not an assembly UP mark.", fill="#496069", font=v2.font(21))
    d.text((55, 1025), "Arrow alone is symmetric. Geometry checks do not verify machine cutting or workshop readability.", fill="#496069", font=v2.font(21))
    image.save(OUT / "laserfont3-front-back.png")

    chars = groups(OUT / "laserfont3-H5-character-samples.dxf")
    image = Image.new("RGB", (1800, 1190), "#f6f4ee")
    d = ImageDraw.Draw(image)
    d.text((45, 25), "LaserFont 3 | Arrow and character set", fill="#182b32", font=v2.font(43))
    d.text((45, 85), "Arrow before the unchanged ID, pointing toward the top of readable lettering. Read them together.", fill="#496069", font=v2.font(25))
    for i, curves in enumerate(chars):
        row, col = divmod(i, 8)
        x, y = 35+col*221, 150+row*191
        d.rounded_rectangle((x,y,x+209,y+175), 8, fill="white", outline="#d8d9d1", width=1)
        draw_paths(d, curves, (x+18,y+20,x+188,y+126), "#067047", width=4)
        d.text((x+15,y+138), "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"[i], font=v2.font(22), fill="#182b32")
    d.text((45,1130), "5 mm sample DXF available. Enlarged display; print the A4 specimen at 100% for physical scale.", fill="#496069", font=v2.font(22))
    image.save(OUT / "laserfont3-alphabet.png")

    # 300 dpi A4 specimen. PDF MediaBox derives from the actual pixel/dpi ratio.
    ppm = 300/25.4
    image = Image.new("RGB", (round(210*ppm), round(297*ppm)), "white")
    d = ImageDraw.Draw(image)
    d.text((15*ppm,13*ppm), "LaserFont 3 | 5 mm specimen", fill="black", font=v2.font(52))
    d.text((15*ppm,23*ppm), "9 October 2026 | Print at 100% / Actual size", fill="black", font=v2.font(29))
    d.text((15*ppm,31*ppm), "Arrow before ID; arrow points toward the top of readable lettering.", fill="black", font=v2.font(28))
    for i, curves in enumerate(saved):
        xmin = min(x for c in curves for x,y in c)
        ymin = min(y for c in curves for x,y in c)
        baseline = 57+i*16
        for c in curves:
            d.line([((20+x-xmin)*ppm,(baseline-(y-ymin))*ppm) for x,y in c], fill="black", width=2)
    y = 200*ppm
    d.line((20*ppm,y,70*ppm,y), fill="black", width=2)
    for x in (20,70): d.line((x*ppm,y-2*ppm,x*ppm,y+2*ppm),fill="black",width=2)
    d.text((20*ppm,205*ppm), "This line must measure 50 mm on paper.", fill="black", font=v2.font(29))
    for i, text in enumerate(("Arrow at 5 mm: 3 mm wide; 1.5 mm gap to the first character.",
                              "Through-cut centerlines; do not close paths or stencil gaps.",
                              "Check the whole label fits inside the part before cutting.",
                              "Actual CAM import and a cut sample remain to be verified.")):
        d.text((15*ppm,(228+i*8)*ppm),text,fill="black",font=v2.font(27))
    image.save(OUT / "laserfont3-H5-print.png")
    image.save(OUT / "laserfont3-H5-print.pdf", resolution=300)


if __name__ == "__main__":
    preview()
    print("Saved DXF-based previews and A4 5 mm specimen in examples/")
