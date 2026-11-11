from __future__ import annotations

import sys
from typing import Any


def clear_screen() -> None:
    sys.stdout.write("\033c")
    sys.stdout.flush()


def print_line(text: str = "") -> None:
    print(text)


def ask_line(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return "q"


def yellow(text: str) -> str:
    return f"\033[1;33m{text}\033[0m"


def select_menu(
    title: str,
    options: list[tuple[str, str]],
    *,
    sep_before: set[str] | None = None,
    initial_index: int = 0,
) -> str | None:
    """Arrow-key menu with yellow highlight.

    options: list of (id, label). Returns selected id, or None on quit/esc/ctrl_c.
    sep_before: option ids that get a blank separator line above them.
    """
    if not options:
        return None
    sep = sep_before or set()
    index = max(0, min(initial_index, len(options) - 1))
    while True:
        clear_screen()
        for line in title.splitlines() or [title]:
            print_line(line)
        print_line()
        for i, (oid, label) in enumerate(options):
            if oid in sep:
                print_line()
            if i == index:
                print_line(yellow(f"> {label}"))
            else:
                print_line(f"  {label}")
        print_line()

        key = read_key()
        if key["type"] == "ctrl_c":
            return None
        if key["type"] == "esc":
            return None
        if key["type"] == "up":
            index = (index - 1) % len(options)
            continue
        if key["type"] == "down":
            index = (index + 1) % len(options)
            continue
        if key["type"] == "enter":
            return options[index][0]
        if key["type"] == "char":
            ch = key["value"].lower()
            if ch in {"q"}:
                return None


def read_key() -> dict[str, Any]:
    """Read one key.

    Returns type: left|right|up|down|enter|esc|backspace|char|ctrl_c|other
    """
    if sys.platform == "win32":
        return _read_key_windows()
    return _read_key_posix()


def read_key_timeout(timeout_sec: float) -> dict[str, Any] | None:
    """Read one key with timeout. Returns None if no key within timeout_sec."""
    if sys.platform == "win32":
        return _read_key_windows_timeout(timeout_sec)
    return _read_key_posix_timeout(timeout_sec)


def _read_key_windows_timeout(timeout_sec: float) -> dict[str, Any] | None:
    import msvcrt
    import time

    deadline = time.monotonic() + max(0.0, timeout_sec)
    while time.monotonic() < deadline:
        if msvcrt.kbhit():
            return _read_key_windows()
        time.sleep(0.02)
    return None


def _read_key_posix_timeout(timeout_sec: float) -> dict[str, Any] | None:
    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ready, _, _ = select.select([fd], [], [], max(0.0, timeout_sec))
        if not ready:
            return None
        return _read_key_posix_from_raw(fd)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _read_key_windows() -> dict[str, Any]:
    import msvcrt

    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        code = msvcrt.getwch()
        if code == "K":
            return {"type": "left"}
        if code == "M":
            return {"type": "right"}
        if code == "H":
            return {"type": "up"}
        if code == "P":
            return {"type": "down"}
        return {"type": "other", "value": code}
    if ch in ("\r", "\n"):
        return {"type": "enter"}
    if ch == "\x1b":
        return {"type": "esc"}
    if ch in ("\x08", "\x7f"):
        return {"type": "backspace"}
    if ch == "\x03":
        return {"type": "ctrl_c"}
    return {"type": "char", "value": ch}


def _read_byte(fd: int) -> str:
    import os

    data = os.read(fd, 1)
    if not data:
        return ""
    return data.decode("utf-8", errors="replace")


def _read_escape_rest(fd: int) -> str:
    """Read remaining CSI bytes after Esc; empty means bare Esc."""
    import termios
    import tty

    attrs = termios.tcgetattr(fd)
    try:
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 1  # 0.1s
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        rest = ""
        while len(rest) < 2:
            chunk = _read_byte(fd)
            if not chunk:
                break
            rest += chunk
        return rest
    finally:
        tty.setraw(fd)


def _read_key_posix_from_raw(fd: int) -> dict[str, Any]:
    """Parse one key while fd is already in raw mode."""
    ch = _read_byte(fd)
    if not ch:
        return {"type": "other", "value": ""}
    if ch == "\x03":
        return {"type": "ctrl_c"}
    if ch in ("\r", "\n"):
        return {"type": "enter"}
    if ch in ("\x7f", "\x08"):
        return {"type": "backspace"}
    if ch == "\x1b":
        rest = _read_escape_rest(fd)
        if rest == "[D":
            return {"type": "left"}
        if rest == "[C":
            return {"type": "right"}
        if rest == "[A":
            return {"type": "up"}
        if rest == "[B":
            return {"type": "down"}
        if not rest:
            return {"type": "esc"}
        return {"type": "other", "value": ch + rest}
    return {"type": "char", "value": ch}


def _read_key_posix() -> dict[str, Any]:
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return _read_key_posix_from_raw(fd)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
