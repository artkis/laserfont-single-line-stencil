# Geometry validation

Install the validation dependencies and run from the package directory:

```sh
python -m pip install -r validation/requirements-validation.txt
python validation/validate_geometry.py --root .
```

The script writes `validation/geometry-report.json`. It independently checks
the source curves, open paths, counter bridges, sampled topology, the circular
arc approximation, and the exact/approximate DXF examples after reopening them.
It does not import the font authoring or export modules.

The report identifies tangent and curvature discontinuities, short arc spans,
the sampling tolerance, source hashes, and dependency versions. A PASS concerns
geometry only. It does not establish acceptance by a CAM application or laser
controller, physical bridge strength, actual piercing count, or cutting time.
