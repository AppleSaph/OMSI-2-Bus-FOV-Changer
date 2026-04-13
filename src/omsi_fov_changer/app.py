from __future__ import annotations

import sys


def run() -> int:
    """Application entrypoint."""

    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PySide6 is not installed. Install dependencies with `python -m pip install -r requirements.txt`."
        ) from exc

    from omsi_fov_changer.services.fov_service import FovService
    from omsi_fov_changer.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow(service=FovService())
    window.show()
    return app.exec()
