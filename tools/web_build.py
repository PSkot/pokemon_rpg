"""Build the browser version of the game with pygbag.

    .venv/bin/python tools/web_build.py          # build into build/web-app/build/web/
    .venv/bin/python tools/web_build.py --serve  # build, then serve on http://localhost:8000

pygbag packs a whole folder (with a main.py at its top) into the page, so
this copies just the game and its assets into build/web-app/ first. The
result in build/web-app/build/web/ is a static site: upload it anywhere
(GitHub Pages, itch.io).
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "build" / "web-app"

MAIN = '''import asyncio

from game.main import main

asyncio.run(main())
'''


def assemble() -> None:
    if APP.exists():
        shutil.rmtree(APP)
    APP.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(ROOT / "game", APP / "game", ignore=ignore)
    shutil.copytree(ROOT / "assets", APP / "assets", ignore=ignore)
    (APP / "main.py").write_text(MAIN)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--serve", action="store_true", help="serve the page on http://localhost:8000")
    args = parser.parse_args()

    assemble()
    # --ume_block 0: start right away instead of waiting for a click (the
    # game has no sound yet, which is what that wait is for).
    command = [sys.executable, "-m", "pygbag", "--ume_block", "0", "--title", "Pokemon RPG"]
    if not args.serve:
        command.append("--build")
    subprocess.run(command + [str(APP)], check=True)


if __name__ == "__main__":
    main()
