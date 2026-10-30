"""Fullscreen in the browser (the page fills the screen, no browser bars).

A page may only go fullscreen while the player is pressing something, and
the game sees a key or tap a frame later. So `toggle` asks right away (a
press a moment ago still counts in most browsers) and, if that's refused,
again when the key or finger is let go (`_JS`'s listeners). iPhones don't
let pages go fullscreen at all (`available` is False there).
"""

import sys

WEB = sys.platform == "emscripten"

# Installed once on the page: requests fullscreen (with Safari's prefixed
# names as a fallback), retried on releases for 3 s after the request (so a
# refused one doesn't go fullscreen out of the blue later); on phones it
# then turns the screen to landscape.
_JS = """
if (!window.pokemonFullscreen) {
  const doc = document, page = doc.documentElement;
  const current = () => doc.fullscreenElement || doc.webkitFullscreenElement;
  const fs = window.pokemonFullscreen = {
    pending: 0,  // when a refused request was made (ms), 0 = none
    available: !!(doc.fullscreenEnabled || doc.webkitFullscreenEnabled),
    on: () => !!current(),
    enter() {
      const request = page.requestFullscreen ? page.requestFullscreen() : page.webkitRequestFullscreen();
      Promise.resolve(request).then(() => {
        fs.pending = 0;
        if (screen.orientation && screen.orientation.lock) screen.orientation.lock("landscape").catch(() => {});
      }).catch(() => {});
    },
    toggle() {
      if (current()) {
        fs.pending = 0;
        Promise.resolve(doc.exitFullscreen ? doc.exitFullscreen() : doc.webkitExitFullscreen()).catch(() => {});
      } else {
        fs.pending = Date.now();
        fs.enter();
      }
    },
  };
  for (const name of ["keyup", "pointerup", "touchend"]) {
    window.addEventListener(name, () => { if (fs.pending && Date.now() - fs.pending < 3000 && !current()) fs.enter(); }, true);
  }
}
"""


_fs = None  # the page's `pokemonFullscreen`, once installed


def _page():
    global _fs
    if _fs is None:
        import platform  # pygbag's: gives access to the page (`window`)
        platform.window.eval(_JS)
        _fs = platform.window.pokemonFullscreen
    return _fs


def available() -> bool:
    """The game runs in a browser that lets it go fullscreen."""
    return WEB and bool(_page().available)


def is_on() -> bool:
    return WEB and bool(_page().on())


def toggle() -> None:
    if WEB:
        _page().toggle()
