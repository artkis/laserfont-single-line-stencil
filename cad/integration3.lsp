;;; SPDX-License-Identifier: MIT
;;; Copyright (c) 2026 Artkis.
;;; AutoCAD display-font setup and one public conversion command: LASEROUT.
;;; The reserved leading ~ displays the key; it is not part of the panel code.

(defun lf3:display-style (/ file data made)
  (setq file (findfile "laserfont3.shx") data (tblsearch "STYLE" "LaserFont3"))
  (cond
    ((not file)
      (princ "\nLaserFont3 display font is not installed. Run Install-LaserFont3.ps1.") nil)
    ((and data
          (or (/= (strcase (vl-filename-base (lf3:get 3 data ""))) "LASERFONT3")
              (/= (lf3:get 4 data "") "")
              (/= (lf3:get 70 data 0) 0)
              (/= (lf3:get 71 data 0) 0)
              (not (equal (lf3:get 40 data 0.0) 0.0 1e-10))
              (not (equal (lf3:get 41 data 1.0) 1.0 1e-10))
              (not (equal (lf3:get 50 data 0.0) 0.0 1e-10))))
      (princ "\nAn incompatible LaserFont3 style exists; it was retained. Use a drawing copy to resolve it.") nil)
    (data "LaserFont3")
    (T
      (setq made (entmake
        '((0 . "STYLE") (100 . "AcDbSymbolTableRecord") (100 . "AcDbTextStyleTableRecord")
          (2 . "LaserFont3") (70 . 0) (40 . 0.0) (41 . 1.0) (50 . 0.0)
          (71 . 0) (42 . 5.0) (3 . "laserfont3.shx") (4 . ""))))
      (if made "LaserFont3" nil))))

(defun c:LASERFONT (/ style)
  (if (setq style (lf3:display-style))
    (progn
      (setvar "TEXTSTYLE" style)
      (setvar "TEXTSIZE" 5.0)
      (princ "\nLaserFont3 selected, default height 5. Create TEXT/MTEXT normally, then use LASEROUT for keyed cut paths.")))
  (princ))

(defun lf3:insert-editable-id (/ *error* txt reason height ins normal angle vec style undo-open made)
  (defun *error* (msg)
    (if undo-open (command-s "_.UNDO" "_End"))
    (if msg (princ (strcat "\nLASEROUT stopped: " msg)))
    (princ))
  (setq txt (getstring T "\nPanel ID (the orientation key is added automatically): ")
        reason (lf3:chars-reason txt))
  (if (/= (logand (lf3:get 70 (tblsearch "LAYER" (getvar "CLAYER")) 0) 4) 0)
    (setq reason "the current layer is locked"))
  (if reason
    (princ (strcat "\nLASEROUT: " reason ". Nothing created."))
    (progn
      (initget 6)
      (setq height (getreal "\nCap height in drawing units <5>: "))
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
              (command-s "_.UNDO" "_Begin")
              (setq undo-open T style (lf3:display-style))
              (if style
                (setq made (entmake
                  (list '(0 . "TEXT") '(100 . "AcDbEntity")
                    (cons 8 (getvar "CLAYER")) '(100 . "AcDbText")
                    (cons 10 ins) (cons 40 height) (cons 1 (strcat "~" (strcase txt)))
                    (cons 50 angle) '(41 . 1.0) '(51 . 0.0) (cons 7 style)
                    '(71 . 0) '(72 . 0) '(11 0.0 0.0 0.0)
                    '(210 0.0 0.0 1.0) '(100 . "AcDbText") '(73 . 0)))))
              (command-s "_.UNDO" "_End")
              (setq undo-open nil)
              (if made
                (princ "\nEditable keyed ID created. Convert with LASEROUT before cutting; do not use TXTEXP.")
                (princ "\nLASEROUT: no text was created."))))))))
  (princ))


;;; Clear old public commands when this file reloads into an existing drawing.
;;; Internal exact/insertion helpers remain available to validation code only.
(setq c:LASEROUT2 nil c:LASEROUT3 nil c:LASERPOLY nil
      c:LASERPOLY2 nil c:LASERPOLY3 nil c:LASER2 nil c:LASER3 nil
      c:LASERTEXT3 nil)
(defun c:LASEROUT () (lf3:command-poly))
(princ "\nLASEROUT loaded: convert plain TEXT/MTEXT to separate polylines with one orientation arrow. No GROUP created. LASERFONT selects the 5 mm default.")
(princ)
