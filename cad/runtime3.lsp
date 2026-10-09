;;; SPDX-License-Identifier: MIT
;;; Copyright (c) 2026 Artkis.
;;; AutoLISP utility program; see LICENSE-MIT.txt for the MIT license.
;;; Font designs and generated embedded glyph/key tables are separately OFL-1.1.
;;; Native named-dictionary grouping keeps each key with its ID.
;;; Validation scope and limitations: native-test-report-v3.json.

(defun lf3:get (code data default / found)
  (if (setq found (assoc code data)) (cdr found) default))

(defun lf3:content (data / pair out)
  (setq out "")
  (foreach pair data
    (if (member (car pair) '(3 1)) (setq out (strcat out (cdr pair)))))
  out)

(defun lf3:font-name (data / style fname ext)
  (setq style (tblsearch "STYLE" (lf3:get 7 data "Standard"))
        fname (lf3:get 3 style "") ext (vl-filename-extension fname))
  (if (or (not ext) (= (strcase ext) ".SHX"))
    (strcase (vl-filename-base fname)) nil))

(defun lf3:font-p (data)
  (member (lf3:font-name data) '("LASERFONT" "LASERFONT2" "LASERFONT3")))

(defun lf3:keyed-text-p (data)
  (and (= (lf3:font-name data) "LASERFONT3")
       (= (substr (lf3:content data) 1 1) "~")))

(defun lf3:label-content (data)
  ;; Only the reserved first character of a v3 display label is metadata.
  ;; Other tildes remain in the content so character validation rejects them.
  (if (lf3:keyed-text-p data) (substr (lf3:content data) 2) (lf3:content data)))

(defun lf3:chars-reason (txt / i raw code ch reason ink)
  (setq i 1 reason nil ink nil)
  (while (and (<= i (strlen txt)) (not reason))
    ;; Reject raw non-ASCII input before case conversion can change its meaning.
    (setq raw (substr txt i 1) code (ascii raw))
    (cond
      ((or (= code 32) (= code 45)))
      ((or (and (>= code 48) (<= code 57))
           (and (>= code 65) (<= code 90))
           (and (>= code 97) (<= code 122)))
        (setq ch (strcase raw))
        (if (assoc ch *lf3:glyphs*) (setq ink T)
          (setq reason "glyph data is unavailable")))
      (T (setq reason "only plain ASCII A-Z, 0-9, hyphen and spaces are supported; remove formatting or line breaks")))
    (setq i (1+ i)))
  (if (and (not reason) (not ink)) (setq reason "the label needs at least one ASCII letter or digit"))
  reason)

(defun lf3:reason (data / kind style layer reason)
  (setq kind (lf3:get 0 data "")
        style (tblsearch "STYLE" (lf3:get 7 data "Standard"))
        layer (tblsearch "LAYER" (lf3:get 8 data "0")))
  (cond
    ((not (member kind '("TEXT" "MTEXT"))) "select TEXT or plain one-line MTEXT")
    ((not (lf3:font-p data)) "the text style does not use laserfont.shx, laserfont2.shx or laserfont3.shx")
    ((/= (lf3:get 4 style "") "") "a bigfont is assigned to the text style")
    ((/= (logand (lf3:get 70 style 0) 4) 0) "vertical text styles are unsupported")
    ((and (= kind "MTEXT")
          (not (or (findfile (lf3:get 3 style ""))
                   (findfile (strcat (vl-filename-base (lf3:get 3 style "")) ".shx")))))
      "the source style's SHX font must be available for native MTEXT baseline resolution")
    ((/= (logand (lf3:get 70 layer 0) 4) 0) "the source layer is locked")
    ((<= (lf3:get 40 data 0.0) 0.0) "text height must be positive")
    ((not (equal (lf3:get 41 style 1.0) 1.0 1e-10)) "text-style width factor must be 1")
    ((not (equal (lf3:get 50 style 0.0) 0.0 1e-10)) "text-style oblique angle must be 0")
    ((/= (lf3:get 71 style 0) 0) "mirrored text styles are unsupported")
    ((not (equal (lf3:get 210 data '(0.0 0.0 1.0)) '(0.0 0.0 1.0) 1e-10)) "text must lie in the WCS XY plane")
    ((not (equal (caddr (lf3:get 10 data '(0.0 0.0 0.0))) 0.0 1e-10)) "text elevation must be zero")
    ((not (equal (lf3:get 39 data 0.0) 0.0 1e-10)) "text thickness must be zero")
    ((and (= kind "TEXT") (not (equal (lf3:get 41 data 1.0) 1.0 1e-10))) "TEXT width factor must be 1")
    ((and (= kind "TEXT") (not (equal (lf3:get 51 data 0.0) 0.0 1e-10))) "TEXT oblique angle must be 0")
    ((and (= kind "TEXT") (/= (lf3:get 71 data 0) 0)) "mirrored or backward TEXT is unsupported")
    ((and (= kind "TEXT") (or (/= (lf3:get 72 data 0) 0) (/= (lf3:get 73 data 0) 0))) "TEXT needs left-baseline justification; MTEXT attachment points are supported")
    ((and (= kind "MTEXT") (not (member (lf3:get 72 data 5) '(1 5)))) "vertical or reversed MTEXT is unsupported")
    ((and (= kind "MTEXT") (/= (lf3:get 75 data 0) 0)) "MTEXT columns are unsupported")
    ((and (= kind "MTEXT") (/= (lf3:get 90 data 0) 0)) "MTEXT background masking is unsupported")
    ((and (= kind "MTEXT") (not (member (lf3:get 71 data 1) '(1 2 3 4 5 6 7 8 9)))) "unsupported MTEXT attachment point")
    (T (lf3:chars-reason (lf3:label-content data)))))

(defun lf3:after (marker / out next)
  (setq next (entnext marker) out nil)
  (while next (setq out (cons next out) next (entnext next)))
  (reverse out))

(defun lf3:erase-list (entities / ent)
  (foreach ent entities (if (entget ent) (entdel ent))))

(defun lf3:cleanup-temp ()
  (if *lf3:temp-marker* (lf3:erase-list (lf3:after *lf3:temp-marker*)))
  (setq *lf3:temp-marker* nil))

(defun lf3:appearance (data / code pair out)
  (setq out nil)
  (foreach code '(67 410 8 62 420 430 440 60 6 370 48)
    (if (setq pair (assoc code data)) (setq out (append out (list pair)))))
  out)

(defun lf3:mtext-baseline (data / clone-list code pair clone made answer)
  ;; Only a temporary plain MTEXT copy is exploded. This is ordinary EXPLODE
  ;; (MTEXT -> TEXT), never TXTEXP. Native AutoCAD supplies the exact baseline.
  (setq *lf3:temp-marker* (entlast)
        clone-list (append '((0 . "MTEXT") (100 . "AcDbEntity"))
                          (lf3:appearance data) '((100 . "AcDbMText"))))
  (foreach code '(10 40 41 46 71 72 7 210 11 73 44)
    (if (setq pair (assoc code data)) (setq clone-list (append clone-list (list pair)))))
  (if (and (not (assoc 11 data)) (setq pair (assoc 50 data)))
    (setq clone-list (append clone-list (list pair))))
  (setq clone-list (append clone-list (list (cons 1 (lf3:content data)))))
  (if (entmake clone-list)
    (progn
      (setq clone (entlast))
      (command-s "_.EXPLODE" clone "")
      (setq made (lf3:after *lf3:temp-marker*))
      (if (and (= (length made) 1)
               (= (lf3:get 0 (entget (car made)) "") "TEXT"))
        (setq answer (entget (car made))))))
  (lf3:cleanup-temp)
  (if (and answer (= (lf3:content answer) (lf3:content data))
           (equal (lf3:get 40 answer 0.0) (lf3:get 40 data 0.0) 1e-9)
           (not (lf3:reason answer)))
    answer nil))

(defun lf3:point (p advance insert scale angle / x y ca sa)
  (setq ca (cos angle) sa (sin angle)
        x (* scale (+ advance (car p))) y (* scale (cadr p)))
  (list (+ (car insert) (- (* x ca) (* y sa)))
        (+ (cadr insert) (+ (* x sa) (* y ca))) 0.0))

(defun lf3:polyline (path advance insert scale angle appearance / items p controls knots)
  ;; Function name retained internally; actual output is LINE or exact SPLINE.
  (setq items (append (list (cons 0 (car path)) '(100 . "AcDbEntity"))
                      (lf3:appearance appearance)))
  (if (= (car path) "LINE")
    (setq items (append items (list '(100 . "AcDbLine")
      (cons 10 (lf3:point (cadr path) advance insert scale angle))
      (cons 11 (lf3:point (caddr path) advance insert scale angle)))))
    (progn
      (setq controls (cadr path) knots (caddr path)
            items (append items (list '(100 . "AcDbSpline") '(210 0.0 0.0 1.0)
              '(70 . 8) '(71 . 3) (cons 72 (length knots))
              (cons 73 (length controls)) '(74 . 0) '(42 . 1e-10) '(43 . 1e-10))))
      (foreach p knots (setq items (append items (list (cons 40 p)))))
      (foreach p controls (setq items (append items
        (list (cons 10 (lf3:point p advance insert scale angle))))))))
  (if (entmake items) (entlast) nil))

(defun lf3:discard-group (/ dictionary)
  (if *lf3:pending-group*
    (progn
      (setq dictionary (cdr (assoc -1 (dictsearch (namedobjdict) "ACAD_GROUP"))))
      (if (and dictionary *lf3:pending-group-name*)
        (dictremove dictionary *lf3:pending-group-name*))
      (if (entget *lf3:pending-group*) (entdel *lf3:pending-group*))))
  (setq *lf3:pending-group* nil *lf3:pending-group-name* nil))

(defun lf3:rollback ()
  (lf3:discard-group)
  (lf3:erase-list *lf3:pending-created*)
  (setq *lf3:pending-created* nil))

(defun lf3:group-id (entities / dictionary name data entity)
  ;; Native dictionary construction also works in isolated AutoCAD Core Console.
  ;; Never replace an existing group. The key is the first entity in this list.
  (setq dictionary (cdr (assoc -1 (dictsearch (namedobjdict) "ACAD_GROUP")))
        name (strcat "LASER3_" (cdr (assoc 5 (entget (car entities))))))
  (if (and dictionary (not (dictsearch dictionary name)))
    (progn
      (setq data '((0 . "GROUP") (100 . "AcDbGroup")
                   (300 . "LaserFont3 orientation key and ID") (70 . 0) (71 . 1)))
      (foreach entity entities (setq data (append data (list (cons 340 entity)))))
      (setq *lf3:pending-group* (entmakex data) *lf3:pending-group-name* name)
      (if (and *lf3:pending-group* (dictadd dictionary name *lf3:pending-group*))
        T
        (progn (lf3:discard-group) nil)))
    nil))

(defun lf3:make-id (txt insert height angle appearance / i offset ch glyph path next made ok)
  ;; Manual origin is the key baseline; text starts 18 normalized units later.
  (setq i 1 offset *lf3:text-origin* made nil ok T
        *lf3:pending-created* nil *lf3:pending-group* nil)
  (if (or (lf3:chars-reason txt) (<= height 0.0)) (setq ok nil))
  (setq txt (strcase txt))
  (if ok
    (if (setq next (lf3:bulged *lf3:key-points* 0.0 insert (/ height 20.0) angle appearance))
      (setq made (list next) *lf3:pending-created* made)
      (setq ok nil)))
  (while (and ok (<= i (strlen txt)))
    (setq ch (substr txt i 1))
    (if (= ch " ") (setq offset (+ offset *lf3:space*))
      (progn
        (setq glyph (assoc ch *lf3:glyphs*))
        (foreach path (caddr glyph)
          (if ok
            (if (setq next (lf3:polyline path offset insert (/ height 20.0) angle appearance))
              (setq made (cons next made) *lf3:pending-created* made)
              (setq ok nil))))
        (setq offset (+ offset (cadr glyph)))))
    (setq i (1+ i)))
  (if (and ok made (lf3:group-id (reverse made)))
    (progn (setq *lf3:pending-created* nil *lf3:pending-group* nil) (reverse made))
    (progn (lf3:rollback) nil)))

(defun lf3:convert (ent / data reason normalized txt i ch glyph path next ok offset insert scale angle made)
  (setq data (entget ent) reason (lf3:reason data))
  (if (not reason)
    (progn
      (setq normalized (if (= (lf3:get 0 data "") "MTEXT") (lf3:mtext-baseline data) data))
      (if (not normalized) (setq reason "MTEXT did not resolve to one plain, unscaled TEXT line; it was kept"))))
  (if reason
    (progn (princ (strcat "\nSkipped " (lf3:get 5 data "") ": " reason ".")) nil)
    (progn
      (setq txt (strcase (lf3:label-content normalized)) i 1
            offset (if (lf3:keyed-text-p normalized) *lf3:text-origin* 0.0)
            insert (cdr (assoc 10 normalized)) scale (/ (cdr (assoc 40 normalized)) 20.0)
            angle (lf3:get 50 normalized 0.0) made nil
            *lf3:pending-created* nil *lf3:pending-group* nil ok T)
      ;; A leading display key already reserves the key advance; bare text does not.
      (if (setq next (lf3:bulged *lf3:key-points*
                        (if (lf3:keyed-text-p normalized) 0.0 (- *lf3:text-origin*))
                        insert scale angle data))
        (setq made (list next) *lf3:pending-created* made)
        (setq ok nil))
      (while (and ok (<= i (strlen txt)))
        (setq ch (substr txt i 1))
        (if (= ch " ")
          (setq offset (+ offset *lf3:space*))
          (progn
            (setq glyph (assoc ch *lf3:glyphs*))
            (foreach path (caddr glyph)
              (if ok
                (if (setq next (lf3:polyline path offset insert scale angle data))
                  (setq made (cons next made) *lf3:pending-created* made)
                  (setq ok nil))))
            (setq offset (+ offset (cadr glyph)))))
        (setq i (1+ i)))
      (if (and ok made (lf3:group-id (reverse made)) (entdel ent))
        (progn (setq *lf3:pending-created* nil *lf3:pending-group* nil) T)
        (progn
          (lf3:rollback)
          (princ (strcat "\nLabel " (lf3:get 5 data "") " kept: no cut paths were committed.")) nil)))))

(defun lf3:command-exact (/ *error* sel index count skipped undo-open)
  (defun *error* (msg)
    (lf3:cleanup-temp)
    (lf3:rollback)
    (if undo-open (command-s "_.UNDO" "_End"))
    (if msg (princ (strcat "\nLASEROUT stopped: " msg ". One UNDO reverses this batch.")))
    (princ))
  (setq *lf3:pending-created* nil *lf3:pending-group* nil *lf3:temp-marker* nil)
  (prompt "\nSelect laserfont/laserfont2/laserfont3 TEXT or plain one-line MTEXT to turn into exact cut paths: ")
  (setq sel (ssget '((0 . "TEXT,MTEXT"))))
  (if sel
    (progn
      (command-s "_.UNDO" "_Begin") (setq undo-open T index 0 count 0 skipped 0)
      (repeat (sslength sel)
        (if (lf3:convert (ssname sel index)) (setq count (1+ count)) (setq skipped (1+ skipped)))
        (setq index (1+ index)))
      (command-s "_.UNDO" "_End") (setq undo-open nil)
      (princ (strcat "\nLASEROUT: " (itoa count) " labels converted; " (itoa skipped)
                     " skipped. Grouped key plus exact Bezier/line glyphs created; stencil bridges retained."
                     " One UNDO reverses this batch."))))
  (princ))

(defun lf3:insert-id (/ *error* txt reason height ins angle vec normal undo-open made)
  (defun *error* (msg)
    (lf3:rollback)
    (if undo-open (command-s "_.UNDO" "_End"))
    (if msg (princ (strcat "\nLASEROUT stopped: " msg))) (princ))
  (setq *lf3:pending-created* nil *lf3:pending-group* nil)
  (setq txt (getstring T "\nPanel ID (A-Z, 0-9, hyphen and spaces): "))
  (if (= txt "") (setq reason "no ID entered") (setq reason (lf3:chars-reason txt)))
  (if (/= (logand (lf3:get 70 (tblsearch "LAYER" (getvar "CLAYER")) 0) 4) 0)
    (setq reason "the current layer is locked"))
  (if reason (princ (strcat "\nLASEROUT: " reason ". Nothing created."))
    (progn
      (initget 6) (setq height (getreal "\nCap height in drawing units <5>: "))
      (if (not height) (setq height 5.0))
      (setq ins (getpoint "\nLeft orientation-key baseline insertion point: "))
      (if ins
        (progn
          (setq ins (trans ins 1 0) normal (trans '(0.0 0.0 1.0) 1 0 T))
          (if (or (not (equal (caddr ins) 0.0 1e-8))
                  (not (equal normal '(0.0 0.0 1.0) 1e-8)))
            (princ "\nLASEROUT: use a WCS XY plane insertion at elevation zero. Nothing created.")
            (progn
              (setq angle (getangle "\nRotation <0>: "))
              (if (not angle) (setq angle 0.0))
              (setq vec (trans (list (cos angle) (sin angle) 0.0) 1 0 T)
                    angle (atan (cadr vec) (car vec)))
              (command-s "_.UNDO" "_Begin") (setq undo-open T)
              (setq made (lf3:make-id txt ins height angle (list (cons 8 (getvar "CLAYER")))))
              (command-s "_.UNDO" "_End") (setq undo-open nil)
              (if made
                (princ (strcat "\nLASEROUT: " (itoa (length made))
                  " open paths created as one key-and-ID group. Permanent geometry; no font needed."))
                (princ "\nLASEROUT: no cut paths were committed."))))))))
  (princ))

(defun lf3:bulged (path advance insert scale angle appearance / items p x y ca sa)
  (setq ca (cos angle) sa (sin angle)
        items (append '((0 . "LWPOLYLINE") (100 . "AcDbEntity"))
          (lf3:appearance appearance)
          (list '(100 . "AcDbPolyline") (cons 90 (length path))
                '(70 . 0) '(43 . 0.0) '(38 . 0.0) '(210 0.0 0.0 1.0))))
  (foreach p path
    (setq x (* scale (+ advance (car p))) y (* scale (cadr p))
          items (append items
            (list (cons 10 (list (+ (car insert) (- (* x ca) (* y sa)))
                                 (+ (cadr insert) (+ (* x sa) (* y ca)))))
                  (cons 42 (caddr p))))))
  (if (entmake items) (entlast) nil))

(defun lf3:convert-poly (ent / data reason normalized txt i ch glyph path next ok offset insert scale angle made)
  (setq data (entget ent) reason (lf3:reason data))
  (if (not *lf3:poly-glyphs*) (setq reason "arc-fit data is unavailable"))
  (if (not reason)
    (progn
      (setq normalized (if (= (lf3:get 0 data "") "MTEXT") (lf3:mtext-baseline data) data))
      (if (not normalized) (setq reason "MTEXT did not resolve to one plain, unscaled TEXT line; it was kept"))))
  (if reason
    (progn (princ (strcat "\nSkipped " (lf3:get 5 data "") ": " reason ".")) nil)
    (progn
      (setq txt (strcase (lf3:label-content normalized)) i 1
            offset (if (lf3:keyed-text-p normalized) *lf3:text-origin* 0.0)
            insert (cdr (assoc 10 normalized)) scale (/ (cdr (assoc 40 normalized)) 20.0)
            angle (lf3:get 50 normalized 0.0) made nil
            *lf3:pending-created* nil *lf3:pending-group* nil ok T)
      ;; A leading display key already reserves the key advance; bare text does not.
      (if (setq next (lf3:bulged *lf3:key-points*
                        (if (lf3:keyed-text-p normalized) 0.0 (- *lf3:text-origin*))
                        insert scale angle data))
        (setq made (list next) *lf3:pending-created* made)
        (setq ok nil))
      (while (and ok (<= i (strlen txt)))
        (setq ch (substr txt i 1))
        (if (= ch " ")
          (setq offset (+ offset *lf3:space*))
          (progn
            (setq glyph (assoc ch *lf3:poly-glyphs*))
            (foreach path (caddr glyph)
              (if ok
                (if (setq next (lf3:bulged path offset insert scale angle data))
                  (setq made (cons next made) *lf3:pending-created* made)
                  (setq ok nil))))
            (setq offset (+ offset (cadr glyph)))))
        (setq i (1+ i)))
      (if (and ok made (lf3:group-id (reverse made)) (entdel ent))
        (progn (setq *lf3:pending-created* nil *lf3:pending-group* nil) T)
        (progn
          (lf3:rollback)
          (princ (strcat "\nLabel " (lf3:get 5 data "") " kept: no cut paths were committed.")) nil)))))

(defun lf3:command-poly (/ *error* sel index count skipped undo-open)
  (defun *error* (msg)
    (lf3:cleanup-temp)
    (lf3:rollback)
    (if undo-open (command-s "_.UNDO" "_End"))
    (if msg (princ (strcat "\nLASEROUT stopped: " msg ". One UNDO reverses this batch.")))
    (princ))
  (setq *lf3:pending-created* nil *lf3:pending-group* nil *lf3:temp-marker* nil)
  (prompt "\nSelect laserfont/laserfont2/laserfont3 TEXT or plain one-line MTEXT to turn into fitted arc/line polylines: ")
  (setq sel (ssget '((0 . "TEXT,MTEXT"))))
  (if sel
    (progn
      (command-s "_.UNDO" "_Begin") (setq undo-open T index 0 count 0 skipped 0)
      (repeat (sslength sel)
        (if (lf3:convert-poly (ssname sel index)) (setq count (1+ count)) (setq skipped (1+ skipped)))
        (setq index (1+ index)))
      (command-s "_.UNDO" "_End") (setq undo-open nil)
      (princ (strcat "\nLASEROUT: " (itoa count) " labels converted; " (itoa skipped)
                     " skipped. Grouped key plus fitted arc glyph polylines created; stencil gaps retained."
                     " One UNDO reverses this batch."))))
  (princ))

(princ)
