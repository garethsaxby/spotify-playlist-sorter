"""Enable ``python -m spotify_playlist_sorter``."""

from __future__ import annotations

import sys

from .cli import main

sys.exit(main())
