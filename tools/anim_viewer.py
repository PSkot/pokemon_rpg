"""Preview the animations in a sprite sheet.

The sheet is a grid of equally sized frames; each row is one animation.
This script builds a self-contained HTML page (the sheet is embedded) and
opens it in your browser, where every row plays side by side.

    python3 tools/anim_viewer.py
    python3 tools/anim_viewer.py assets/sprites/pixellab/bulbasaur.png --frame 64 \
        --rows walk run jump attack --fps 8

Uses only the Python standard library.
"""

import argparse
import base64
import json
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SHEET = ROOT / "assets" / "sprites" / "pixellab" / "bulbasaur.png"
DEFAULT_ROWS = ["walk", "run", "jump", "attack"]

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>__TITLE__</title>
<style>
  body { margin: 0; padding: 16px 24px; background: #2b2d31; color: #e6e6e6;
         font: 14px system-ui, sans-serif; }
  h1 { font-size: 18px; margin: 0 0 12px; }
  .controls { display: flex; flex-wrap: wrap; gap: 18px; align-items: center;
              padding: 10px 14px; background: #383a40; border-radius: 8px; margin-bottom: 18px; }
  .controls label { display: flex; gap: 6px; align-items: center; }
  button { background: #4e5058; color: #fff; border: 0; border-radius: 6px; padding: 6px 12px;
           font: inherit; cursor: pointer; }
  button:hover { background: #6d6f78; }
  .rows { display: flex; flex-wrap: wrap; gap: 18px; }
  .anim { background: #383a40; border-radius: 8px; padding: 12px; }
  .anim h2 { font-size: 15px; margin: 0 0 8px; display: flex; justify-content: space-between; gap: 12px; }
  .anim h2 span { color: #a0a3ab; font-weight: normal; }
  canvas { image-rendering: pixelated; display: block; }
  canvas.stage { border-radius: 4px; }
  .strip { display: flex; gap: 4px; margin-top: 8px; }
  .strip canvas { border: 2px solid transparent; border-radius: 3px; cursor: pointer; }
  .strip canvas.on { border-color: #f0c040; }
  .bg-checker canvas.stage { background: repeating-conic-gradient(#d8d8d0 0 25%, #f0f0ea 0 50%) 0 0 / 16px 16px; }
  .bg-dark canvas.stage { background: #1e1f22; }
  .bg-grass canvas.stage { background: #8fd16a; }
</style>
<h1>__TITLE__</h1>
<div class="controls">
  <button id="play">Pause</button>
  <button id="step">Step</button>
  <label>FPS <input id="fps" type="range" min="1" max="24" value="__FPS__"><b id="fpsv">__FPS__</b></label>
  <label>Zoom <input id="zoom" type="range" min="1" max="8" value="4"><b id="zoomv">4x</b></label>
  <label><input id="flip" type="checkbox"> Face other way</label>
  <label>Background
    <select id="bg"><option value="checker">checker</option><option value="dark">dark</option>
    <option value="grass">grass</option></select></label>
</div>
<div class="rows bg-checker" id="rows"></div>
<script>
const CFG = __CFG__;
const sheet = new Image();
const state = { playing: true, fps: CFG.fps, zoom: 4, flip: false, tick: 0 };
const anims = [];

function frameIsEmpty(ctx, x, y) {
  const d = ctx.getImageData(x, y, CFG.fw, CFG.fh).data;
  for (let i = 3; i < d.length; i += 4) if (d[i] > 0) return false;
  return true;
}

function drawFrame(canvas, f, scale, flip) {
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = false;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (flip) { ctx.translate(canvas.width, 0); ctx.scale(-1, 1); }
  ctx.drawImage(sheet, f.x, f.y, CFG.fw, CFG.fh, 0, 0, CFG.fw * scale, CFG.fh * scale);
}

function build() {
  // find the non-empty frames in each row
  const probe = document.createElement("canvas");
  probe.width = sheet.width; probe.height = sheet.height;
  const pctx = probe.getContext("2d");
  pctx.drawImage(sheet, 0, 0);
  const cols = Math.floor(sheet.width / CFG.fw), rows = Math.floor(sheet.height / CFG.fh);
  const host = document.getElementById("rows");
  for (let r = 0; r < rows; r++) {
    const frames = [];
    for (let c = 0; c < cols; c++) {
      const x = c * CFG.fw, y = r * CFG.fh;
      if (!frameIsEmpty(pctx, x, y)) frames.push({ x, y });
    }
    if (!frames.length) continue;
    const name = CFG.rows[r] || `row ${r + 1}`;
    const box = document.createElement("div");
    box.className = "anim";
    box.innerHTML = `<h2>${name}<span>row ${r + 1} · ${frames.length} frames</span></h2>`;
    const stage = document.createElement("canvas");
    stage.className = "stage";
    box.appendChild(stage);
    const strip = document.createElement("div");
    strip.className = "strip";
    const thumbs = frames.map((f, i) => {
      const t = document.createElement("canvas");
      t.width = CFG.fw; t.height = CFG.fh;
      t.title = `frame ${i + 1}`;
      t.onclick = () => { state.playing = false; syncPlay(); anim.i = i; render(); };
      strip.appendChild(t);
      return t;
    });
    box.appendChild(strip);
    host.appendChild(box);
    const anim = { frames, stage, thumbs, i: 0 };
    anims.push(anim);
  }
  resize();
  requestAnimationFrame(loop);
}

function resize() {
  for (const a of anims) {
    a.stage.width = CFG.fw * state.zoom;
    a.stage.height = CFG.fh * state.zoom;
    a.frames.forEach((f, i) => drawFrame(a.thumbs[i], f, 1, state.flip));
  }
  render();
}

function render() {
  for (const a of anims) {
    drawFrame(a.stage, a.frames[a.i], state.zoom, state.flip);
    a.thumbs.forEach((t, i) => t.classList.toggle("on", i === a.i));
  }
}

function advance() {
  for (const a of anims) a.i = (a.i + 1) % a.frames.length;
  render();
}

let last = 0;
function loop(t) {
  if (state.playing && t - last >= 1000 / state.fps) { last = t; advance(); }
  requestAnimationFrame(loop);
}

function syncPlay() { document.getElementById("play").textContent = state.playing ? "Pause" : "Play"; }

document.getElementById("play").onclick = () => { state.playing = !state.playing; syncPlay(); };
document.getElementById("step").onclick = () => { state.playing = false; syncPlay(); advance(); };
document.getElementById("fps").oninput = e => {
  state.fps = +e.target.value; document.getElementById("fpsv").textContent = state.fps; };
document.getElementById("zoom").oninput = e => {
  state.zoom = +e.target.value; document.getElementById("zoomv").textContent = state.zoom + "x"; resize(); };
document.getElementById("flip").onchange = e => { state.flip = e.target.checked; resize(); };
document.getElementById("bg").onchange = e => {
  document.getElementById("rows").className = "rows bg-" + e.target.value; };

sheet.onload = build;
sheet.src = CFG.src;
</script>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheet", nargs="?", type=Path, default=DEFAULT_SHEET, help="sprite sheet PNG")
    ap.add_argument("--frame", type=int, nargs="+", default=[64], metavar="PX",
                    help="frame size: one number for square frames, or WIDTH HEIGHT (default 64)")
    ap.add_argument("--rows", nargs="*", default=DEFAULT_ROWS, help="names for each row, top to bottom")
    ap.add_argument("--fps", type=int, default=8, help="starting playback speed (default 8)")
    ap.add_argument("--out", type=Path, help="where to save the HTML (default: build/anim_viewer_<name>.html)")
    ap.add_argument("--no-open", action="store_true", help="only write the HTML, don't open a browser")
    args = ap.parse_args()

    fw, fh = (args.frame * 2)[:2]
    data = base64.b64encode(args.sheet.read_bytes()).decode()
    cfg = {"src": f"data:image/png;base64,{data}", "fw": fw, "fh": fh,
           "rows": args.rows, "fps": args.fps}
    html = (PAGE.replace("__TITLE__", f"{args.sheet.stem} animations")
                .replace("__FPS__", str(args.fps))
                .replace("__CFG__", json.dumps(cfg)))

    # Saved inside the project rather than /tmp: snap-packaged Firefox can't read /tmp.
    out = args.out or ROOT / "build" / f"anim_viewer_{args.sheet.stem}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"wrote {out}")
    if not args.no_open:
        webbrowser.open(out.resolve().as_uri())


if __name__ == "__main__":
    main()
