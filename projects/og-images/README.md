# Open Graph share images

This folder holds the generator (`generate.py`) for the auto-built
1200×630 PNG share images stored in [`assets/og/`](../../assets/og/).

It runs from the
[`og-images` workflow](../../.github/workflows/og-images.yml)
on every push that touches a content file, and commits the regenerated
PNGs back to the same branch with `[skip ci]`.

Local run:

```bash
pip install Pillow PyYAML
python projects/og-images/generate.py
```
