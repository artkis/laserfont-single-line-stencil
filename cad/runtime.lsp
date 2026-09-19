;;; SPDX-License-Identifier: MIT
;;; Copyright (c) 2026 Artkis.
;;; AutoLISP utility program; see LICENSE-MIT.txt for the MIT license.
;;; Font designs and generated embedded glyph tables are separately OFL-1.1.

(defun lf2:get (code data default / found)
  (if (setq found (assoc code data)) (cdr found) default))

(defun lf2:content (data / pair out)
  (setq out "")
  (foreach pair data
    (if (member (car pair) '(3 1)) (setq out (strcat out (cdr pair)))))
  out)

(defun lf2:font-p (data / style fname ext)
  (setq style (tblsearch "STYLE" (lf2:get 7 data "Standard"))
        fname (lf2:get 3 style "") ext (vl-filename-extension fname))
  (and (= (strcase (vl-filename-base fname)) "LASERFONT2")
       (or (not ext) (= (strcase ext) ".SHX"))))

(defun lf2:chars-reason (txt / i ch reason ink)
  (setq i 1 reason nil ink nil)
  (while (and (<= i (strlen txt)) (not reason))
    (setq ch (strcase (substr txt i 1)))
    (cond
      ((= ch " "))
      ((assoc ch *lf2:glyphs*) (setq ink T))
      (T (setq reason "only plain A-Z, 0-9, hyphen and spaces are supported; remove formatting or line breaks")))
    (setq i (1+ i)))
  (if (and (not reason) (not ink)) (setq reason "the label has no supported letters or digits"))
  reason)

(defun lf2:reason (data / kind style layer reason)
  (setq kind (lf2:get 0 data "")
        style (tblsearch "STYLE" (lf2:get 7 data "Standard"))
        layer (tblsearch "LAYER" (lf2:get 8 data "0")))
  (cond
    ((not (member kind '("TEXT" "MTEXT"))) "select TEXT or plain one-line MTEXT")
    ((not (lf2:font-p data)) "the text style does not use laserfont2.shx")
    ((/= (lf2:get 4 style "") "") "a bigfont is assigned to the text style")
    ((/= (logand (lf2:get 70 style 0) 4) 0) "vertical text styles are unsupported")
    ((and (= kind "MTEXT")
          (not (or (findfile (lf2:get 3 style "laserfont2.shx")) (findfile "laserfont2.shx"))))
      "laserfont2.shx must be available for native MTEXT baseline resolution")
    ((/= (logand (lf2:get 70 layer 0) 4) 0) "the source layer is locked")
    ((<= (lf2:get 40 data 0.0) 0.0) "text height must be positive")
    ((not (equal (lf2:get 41 style 1.0) 1.0 1e-10)) "text-style width factor must be 1")
    ((not (equal (lf2:get 50 style 0.0) 0.0 1e-10)) "text-style oblique angle must be 0")
    ((/= (lf2:get 71 style 0) 0) "mirrored text styles are unsupported")
    ((not (equal (lf2:get 210 data '(0.0 0.0 1.0)) '(0.0 0.0 1.0) 1e-10)) "text must lie in the WCS XY plane")
    ((not (equal (caddr (lf2:get 10 data '(0.0 0.0 0.0))) 0.0 1e-10)) "text elevation must be zero")
    ((not (equal (lf2:get 39 data 0.0) 0.0 1e-10)) "text thickness must be zero")
    ((and (= kind "TEXT") (not (equal (lf2:get 41 data 1.0) 1.0 1e-10))) "TEXT width factor must be 1")
    ((and (= kind "TEXT") (not (equal (lf2:get 51 data 0.0) 0.0 1e-10))) "TEXT oblique angle must be 0")
    ((and (= kind "TEXT") (/= (lf2:get 71 data 0) 0)) "mirrored or backward TEXT is unsupported")
    ((and (= kind "TEXT") (or (/= (lf2:get 72 data 0) 0) (/= (lf2:get 73 data 0) 0))) "TEXT needs left-baseline justification; MTEXT attachment points are supported")
    ((and (= kind "MTEXT") (not (member (lf2:get 72 data 5) '(1 5)))) "vertical or reversed MTEXT is unsupported")
    ((and (= kind "MTEXT") (/= (lf2:get 75 data 0) 0)) "MTEXT columns are unsupported")
    ((and (= kind "MTEXT") (/= (lf2:get 90 data 0) 0)) "MTEXT background masking is unsupported")
    ((and (= kind "MTEXT") (not (member (lf2:get 71 data 1) '(1 2 3 4 5 6 7 8 9)))) "unsupported MTEXT attachment point")
    (T (lf2:chars-reason (lf2:content data)))))

(defun lf2:after (marker / out next)
  (setq next (entnext marker) out nil)
  (while next (setq out (cons next out) next (entnext next)))
  (reverse out))

(defun lf2:erase-list (entities / ent)
  (foreach ent entities (if (entget ent) (entdel ent))))

(defun lf2:cleanup-temp ()
  (if *lf2:temp-marker* (lf2:erase-list (lf2:after *lf2:temp-marker*)))
  (setq *lf2:temp-marker* nil))

(defun lf2:appearance (data / code pair out)
  (setq out nil)
  (foreach code '(67 410 8 62 420 430 440 60 6 370 48)
    (if (setq pair (assoc code data)) (setq out (append out (list pair)))))
  out)

(defun lf2:mtext-baseline (data / clone-list code pair clone made answer)
  ;; Only a temporary plain MTEXT copy is exploded. This is ordinary EXPLODE
  ;; (MTEXT -> TEXT), never TXTEXP. Native AutoCAD supplies the exact baseline.
  (setq *lf2:temp-marker* (entlast)
        clone-list (append '((0 . "MTEXT") (100 . "AcDbEntity"))
                          (lf2:appearance data) '((100 . "AcDbMText"))))
  (foreach code '(10 40 41 46 71 72 7 210 11 73 44)
    (if (setq pair (assoc code data)) (setq clone-list (append clone-list (list pair)))))
  (if (and (not (assoc 11 data)) (setq pair (assoc 50 data)))
    (setq clone-list (append clone-list (list pair))))
  (setq clone-list (append clone-list (list (cons 1 (lf2:content data)))))
  (if (entmake clone-list)
    (progn
      (setq clone (entlast))
      (command-s "_.EXPLODE" clone "")
      (setq made (lf2:after *lf2:temp-marker*))
      (if (and (= (length made) 1)
               (= (lf2:get 0 (entget (car made)) "") "TEXT"))
        (setq answer (entget (car made))))))
  (lf2:cleanup-temp)
  (if (and answer (= (lf2:content answer) (lf2:content data))
           (equal (lf2:get 40 answer 0.0) (lf2:get 40 data 0.0) 1e-9)
           (not (lf2:reason answer)))
    answer nil))

(defun lf2:point (p advance insert scale angle / x y ca sa)
  (setq ca (cos angle) sa (sin angle)
        x (* scale (+ advance (car p))) y (* scale (cadr p)))
  (list (+ (car insert) (- (* x ca) (* y sa)))
        (+ (cadr insert) (+ (* x sa) (* y ca))) 0.0))

(defun lf2:polyline (path advance insert scale angle appearance / items p controls knots)
  ;; Function name retained internally; actual output is LINE or exact SPLINE.
  (setq items (append (list (cons 0 (car path)) '(100 . "AcDbEntity"))
                      (lf2:appearance appearance)))
  (if (= (car path) "LINE")
    (setq items (append items (list '(100 . "AcDbLine")
      (cons 10 (lf2:point (cadr path) advance insert scale angle))
      (cons 11 (lf2:point (caddr path) advance insert scale angle)))))
    (progn
      (setq controls (cadr path) knots (caddr path)
            items (append items (list '(100 . "AcDbSpline") '(210 0.0 0.0 1.0)
              '(70 . 8) '(71 . 3) (cons 72 (length knots))
              (cons 73 (length controls)) '(74 . 0) '(42 . 1e-10) '(43 . 1e-10))))
      (foreach p knots (setq items (append items (list (cons 40 p)))))
      (foreach p controls (setq items (append items
        (list (cons 10 (lf2:point p advance insert scale angle))))))))
  (if (entmake items) (entlast) nil))

(defun lf2:make-id (txt insert height angle appearance / i offset ch glyph path next made ok)
  (setq txt (strcase txt) i 1 offset 0.0 made nil ok T *lf2:pending-created* nil)
  (if (or (lf2:chars-reason txt) (<= height 0.0)) (setq ok nil))
  (while (and ok (<= i (strlen txt)))
    (setq ch (substr txt i 1))
    (if (= ch " ") (setq offset (+ offset *lf2:space*))
      (progn
        (setq glyph (assoc ch *lf2:glyphs*))
        (foreach path (caddr glyph)
          (if ok
            (if (setq next (lf2:polyline path offset insert (/ height 20.0) angle appearance))
              (setq made (cons next made) *lf2:pending-created* made)
              (setq ok nil))))
        (setq offset (+ offset (cadr glyph)))))
    (setq i (1+ i)))
  (if (and ok made) (progn (setq *lf2:pending-created* nil) (reverse made))
    (progn (lf2:erase-list made) (setq *lf2:pending-created* nil) nil)))

(defun lf2:convert (ent / data reason normalized txt i ch glyph path next ok offset insert scale angle made)
  (setq data (entget ent) reason (lf2:reason data))
  (if (not reason)
    (progn
      (setq normalized (if (= (lf2:get 0 data "") "MTEXT") (lf2:mtext-baseline data) data))
      (if (not normalized) (setq reason "MTEXT did not resolve to one plain, unscaled TEXT line; it was kept"))))
  (if reason
    (progn (princ (strcat "\nSkipped " (lf2:get 5 data "") ": " reason ".")) nil)
    (progn
      (setq txt (strcase (lf2:content normalized)) i 1 offset 0.0
            insert (cdr (assoc 10 normalized)) scale (/ (cdr (assoc 40 normalized)) 20.0)
            angle (lf2:get 50 normalized 0.0) made nil *lf2:pending-created* nil ok T)
      (while (and ok (<= i (strlen txt)))
        (setq ch (substr txt i 1))
        (if (= ch " ")
          (setq offset (+ offset *lf2:space*))
          (progn
            (setq glyph (assoc ch *lf2:glyphs*))
            (foreach path (caddr glyph)
              (if ok
                (if (setq next (lf2:polyline path offset insert scale angle data))
                  (setq made (cons next made) *lf2:pending-created* made)
                  (setq ok nil))))
            (setq offset (+ offset (cadr glyph)))))
        (setq i (1+ i)))
      (if (and ok made (entdel ent))
        (progn (setq *lf2:pending-created* nil) T)
        (progn
          (lf2:erase-list made) (setq *lf2:pending-created* nil)
          (princ (strcat "\nLabel " (lf2:get 5 data "") " kept: no cut paths were committed.")) nil)))))

(defun c:LASEROUT2 (/ *error* sel index count skipped undo-open)
  (defun *error* (msg)
    (lf2:cleanup-temp)
    (lf2:erase-list *lf2:pending-created*)
    (setq *lf2:pending-created* nil)
    (if undo-open (command-s "_.UNDO" "_End"))
    (if msg (princ (strcat "\nLASEROUT2 stopped: " msg ". One UNDO reverses completed labels in this batch.")))
    (princ))
  (setq *lf2:pending-created* nil *lf2:temp-marker* nil)
  (prompt "\nSelect laserfont2 TEXT or plain one-line MTEXT to turn into exact cut paths: ")
  (setq sel (ssget '((0 . "TEXT,MTEXT"))))
  (if sel
    (progn
      (command-s "_.UNDO" "_Begin") (setq undo-open T index 0 count 0 skipped 0)
      (repeat (sslength sel)
        (if (lf2:convert (ssname sel index)) (setq count (1+ count)) (setq skipped (1+ skipped)))
        (setq index (1+ index)))
      (command-s "_.UNDO" "_End") (setq undo-open nil)
      (princ (strcat "\nLASEROUT2: " (itoa count) " labels converted; " (itoa skipped)
                     " skipped. Exact Bezier splines/lines and stencil bridges retained."
                     " One UNDO restores this batch."))))
  (princ))

(defun c:LASER2 (/ *error* txt reason height ins angle vec normal undo-open made)
  (defun *error* (msg)
    (lf2:erase-list *lf2:pending-created*)
    (setq *lf2:pending-created* nil)
    (if undo-open (command-s "_.UNDO" "_End"))
    (if msg (princ (strcat "\nLASER2 stopped: " msg))) (princ))
  (setq *lf2:pending-created* nil)
  (setq txt (getstring T "\nPanel ID (A-Z, 0-9, hyphen and spaces): "))
  (if (= txt "") (setq reason "no ID entered") (setq reason (lf2:chars-reason txt)))
  (if (/= (logand (lf2:get 70 (tblsearch "LAYER" (getvar "CLAYER")) 0) 4) 0)
    (setq reason "the current layer is locked"))
  (if reason (princ (strcat "\nLASER2: " reason ". Nothing created."))
    (progn
      (initget 6) (setq height (getreal "\nCap height in drawing units <20>: "))
      (if (not height) (setq height 20.0))
      (setq ins (getpoint "\nLeft baseline insertion point: "))
      (if ins
        (progn
          (setq ins (trans ins 1 0) normal (trans '(0.0 0.0 1.0) 1 0 T))
          (if (or (not (equal (caddr ins) 0.0 1e-8))
                  (not (equal normal '(0.0 0.0 1.0) 1e-8)))
            (princ "\nLASER2: use a WCS XY plane insertion at elevation zero. Nothing created.")
            (progn
              (setq angle (getangle "\nRotation <0>: "))
              (if (not angle) (setq angle 0.0))
              (setq vec (trans (list (cos angle) (sin angle) 0.0) 1 0 T)
                    angle (atan (cadr vec) (car vec)))
              (command-s "_.UNDO" "_Begin") (setq undo-open T)
              (setq made (lf2:make-id txt ins height angle (list (cons 8 (getvar "CLAYER")))))
              (command-s "_.UNDO" "_End") (setq undo-open nil)
              (if made
                (princ (strcat "\nLASER2: " (itoa (length made))
                  " open Bezier/line paths created. Permanent geometry; no font needed."))
                (princ "\nLASER2: no cut paths were committed."))))))))
  (princ))

(defun lf2:bulged (path advance insert scale angle appearance / items p x y ca sa)
  (setq ca (cos angle) sa (sin angle)
        items (append '((0 . "LWPOLYLINE") (100 . "AcDbEntity"))
          (lf2:appearance appearance)
          (list '(100 . "AcDbPolyline") (cons 90 (length path))
                '(70 . 0) '(43 . 0.0) '(38 . 0.0) '(210 0.0 0.0 1.0))))
  (foreach p path
    (setq x (* scale (+ advance (car p))) y (* scale (cadr p))
          items (append items
            (list (cons 10 (list (+ (car insert) (- (* x ca) (* y sa)))
                                 (+ (cadr insert) (+ (* x sa) (* y ca)))))
                  (cons 42 (caddr p))))))
  (if (entmake items) (entlast) nil))

(defun lf2:convert-poly (ent / data reason normalized txt i ch glyph path next ok offset insert scale angle made)
  (setq data (entget ent) reason (lf2:reason data))
  (if (not *lf2:poly-glyphs*) (setq reason "arc-fit data is unavailable"))
  (if (not reason)
    (progn
      (setq normalized (if (= (lf2:get 0 data "") "MTEXT") (lf2:mtext-baseline data) data))
      (if (not normalized) (setq reason "MTEXT did not resolve to one plain, unscaled TEXT line; it was kept"))))
  (if reason
    (progn (princ (strcat "\nSkipped " (lf2:get 5 data "") ": " reason ".")) nil)
    (progn
      (setq txt (strcase (lf2:content normalized)) i 1 offset 0.0
            insert (cdr (assoc 10 normalized)) scale (/ (cdr (assoc 40 normalized)) 20.0)
            angle (lf2:get 50 normalized 0.0) made nil *lf2:pending-created* nil ok T)
      (while (and ok (<= i (strlen txt)))
        (setq ch (substr txt i 1))
        (if (= ch " ")
          (setq offset (+ offset *lf2:space*))
          (progn
            (setq glyph (assoc ch *lf2:poly-glyphs*))
            (foreach path (caddr glyph)
              (if ok
                (if (setq next (lf2:bulged path offset insert scale angle data))
                  (setq made (cons next made) *lf2:pending-created* made)
                  (setq ok nil))))
            (setq offset (+ offset (cadr glyph)))))
        (setq i (1+ i)))
      (if (and ok made (entdel ent))
        (progn (setq *lf2:pending-created* nil) T)
        (progn
          (lf2:erase-list made) (setq *lf2:pending-created* nil)
          (princ (strcat "\nLabel " (lf2:get 5 data "") " kept: no cut paths were committed.")) nil)))))

(defun c:LASERPOLY2 (/ *error* sel index count skipped undo-open)
  (defun *error* (msg)
    (lf2:cleanup-temp)
    (lf2:erase-list *lf2:pending-created*)
    (setq *lf2:pending-created* nil)
    (if undo-open (command-s "_.UNDO" "_End"))
    (if msg (princ (strcat "\nLASERPOLY2 stopped: " msg ". One UNDO reverses completed labels in this batch.")))
    (princ))
  (setq *lf2:pending-created* nil *lf2:temp-marker* nil)
  (prompt "\nSelect laserfont2 TEXT or plain one-line MTEXT to turn into fitted arc/line polylines: ")
  (setq sel (ssget '((0 . "TEXT,MTEXT"))))
  (if sel
    (progn
      (command-s "_.UNDO" "_Begin") (setq undo-open T index 0 count 0 skipped 0)
      (repeat (sslength sel)
        (if (lf2:convert-poly (ssname sel index)) (setq count (1+ count)) (setq skipped (1+ skipped)))
        (setq index (1+ index)))
      (command-s "_.UNDO" "_End") (setq undo-open nil)
      (princ (strcat "\nLASERPOLY2: " (itoa count) " labels converted; " (itoa skipped)
                     " skipped. Fitted circular-arc polylines created; stencil gaps retained."
                     " One UNDO restores this batch."))))
  (princ))

(princ "\nLASER2 loaded: LASER2 creates Bezier IDs; LASEROUT2 converts to Beziers; LASERPOLY2 converts to fitted arc polylines.")
(princ)
