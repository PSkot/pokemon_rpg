"""Start the game: `python -m game` (from the project root)."""

import asyncio

if __package__:
    from .main import main
else:
    # Run as a plain script (e.g. `python game`): make the project root
    # importable so the `game` package can be found.
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from game.main import main

asyncio.run(main())
