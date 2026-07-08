from __future__ import annotations

import tkinter as tk

import pytest


def test_gui_builds_without_display_errors() -> None:
    """Smoke test that the GUI widgets construct without raising.

    Skips automatically when no display/Tk backend is available (e.g. some
    headless CI runners), since that is an environment limitation rather
    than a code issue.
    """
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"No display available for Tk: {exc}")
        return

    try:
        from lecture_splitter.gui import LectureSplitterGUI

        app = LectureSplitterGUI(root)
        assert app.run_button is not None
        assert app.status_label.cget("text") == "대기 중"
    finally:
        root.destroy()
