# Face previews

What the grow clock's panel draws, rendered on the desk instead of on the
panel, from the same numbers the firmware lambdas use.

```bash
pip install pillow
python3 grow_faces.py     # grow-faces.png: every face x every state, both panels
python3 grow_anim.py      # grow-anim-<state>.gif, grow-anim-strip.png, a variety report
```

The scripts look for the Roboto TTF that ESPHome downloaded for the build
(`../.esphome/font/Roboto@400@False@v1.ttf` after an `esphome compile` beside
the YAML); set `GROW_PREVIEW_FONT=/path/to/Roboto-Regular.ttf` to point them
elsewhere, or they fall back to DejaVu and the layout still renders.

- `esphome_canvas.py` — a stand-in for ESPHome's `Display` API on a PIL
  canvas: `fill`, `filled_rectangle`, `filled_circle`, `filled_triangle`,
  `line`, `print` with `TextAlign`, same argument order.
- `grow_faces.py` — the palette, the eye primitive, the resting pose of each
  state, and the still sheet.
- `grow_anim.py` — the eye animator: the clip library, the weighted tables,
  the envelopes and the LCG, and a renderer for GIFs and the clip strip.

**These are mirrors of `../mini-round-clock-with-display.yaml`, kept in step
by hand.** The YAML runs on the clock; the preview only shows. When they
disagree, the panel is right and the preview is wrong — fix the preview, and
say so in the build log.
