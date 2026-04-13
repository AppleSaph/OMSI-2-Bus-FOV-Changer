from __future__ import annotations

import sys
from pathlib import Path


# Support running from source checkout without installing the package.
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from omsi_fov_changer.app import run


if __name__ == "__main__":
    raise SystemExit(run())
