#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.learn import learn_mode
from lib.search import search_mode
from lib.ui import clear_screen, print_line, select_menu


def select_pattern() -> None:
    options = [
        ("search", "search"),
        ("learn", "learn"),
        ("quit", "quit"),
    ]
    while True:
        choice = select_menu("========== FAST IELTS ==========", options)
        if choice is None or choice == "quit":
            clear_screen()
            print_line("stopped.")
            return
        if choice == "search":
            search_mode()
            continue
        if choice == "learn":
            learn_mode()
            continue


def main() -> None:
    select_pattern()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_line("\nstopped.")
        sys.exit(0)
