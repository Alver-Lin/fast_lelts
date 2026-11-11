from __future__ import annotations

import shutil
import subprocess
import sys

from .books import (
    convert_books,
    has_json,
    list_md_books,
    list_unconverted_books,
    load_book,
    save_book,
)
from .note_editor import edit_note
from .ui import (
    ask_line,
    clear_screen,
    green,
    print_line,
    read_key,
    read_key_timeout,
    red,
    select_menu,
    yellow,
)

_PREFERRED_EN_VOICES = ("Samantha", "Daniel", "Alex")
_PREFERRED_ZH_VOICES = ("Tingting", "Meijia", "Sinji")
_cached_en_voice: str | None | bool = False
_cached_zh_voice: str | None | bool = False


def _list_say_voices() -> set[str]:
    try:
        out = subprocess.check_output(
            ["say", "-v", "?"],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except Exception:
        return set()
    return {line.split()[0] for line in out.splitlines() if line.strip()}


def _pick_voice(preferred: tuple[str, ...], cache_attr: str) -> str | None:
    cached = globals()[cache_attr]
    if cached is not False:
        return cached  # type: ignore[return-value]
    available = _list_say_voices()
    picked: str | None = None
    for voice in preferred:
        if voice in available:
            picked = voice
            break
    globals()[cache_attr] = picked
    return picked


def _say_available() -> bool:
    return sys.platform == "darwin" and bool(shutil.which("say"))


def speak_word(word: str) -> bool:
    """Speak English word via macOS `say` (non-blocking)."""
    text = (word or "").strip()
    if not text or not _say_available():
        return False
    cmd = ["say"]
    voice = _pick_voice(_PREFERRED_EN_VOICES, "_cached_en_voice")
    if voice:
        cmd.extend(["-v", voice])
    cmd.append(text)
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _speak_interruptible(text: str, *, lang: str = "en") -> str:
    """Speak text; return 'done' | 'quit' | 'fail'."""
    content = (text or "").strip()
    if not content:
        return "done"
    if not _say_available():
        return "fail"

    cmd = ["say"]
    if lang == "zh":
        voice = _pick_voice(_PREFERRED_ZH_VOICES, "_cached_zh_voice")
    else:
        voice = _pick_voice(_PREFERRED_EN_VOICES, "_cached_en_voice")
    if voice:
        cmd.extend(["-v", voice])
    cmd.append(content)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return "fail"

    while proc.poll() is None:
        key = read_key_timeout(0.1)
        if key is None:
            continue
        if key["type"] == "ctrl_c":
            proc.terminate()
            return "quit"
        if key["type"] == "char" and key["value"].lower() == "q":
            proc.terminate()
            return "quit"
    return "done"


def _pause_or_quit(seconds: float) -> bool:
    """Sleep up to seconds; return True if user pressed q."""
    remaining = max(0.0, seconds)
    while remaining > 0:
        step = min(0.1, remaining)
        key = read_key_timeout(step)
        remaining -= step
        if key is None:
            continue
        if key["type"] == "ctrl_c":
            return True
        if key["type"] == "char" and key["value"].lower() == "q":
            return True
    return False


def entry_status(entry: dict) -> str:
    return entry.get("status") or "unknow"


def filter_entries(entries: list, status_filter: str) -> list:
    if status_filter == "all":
        return list(entries)
    return [e for e in entries if entry_status(e) == status_filter]


def change_status_filter(
    book: str,
    all_entries: list,
    current_filter: str,
) -> str | None:
    """Pick status filter; None keeps current."""
    unknow_n = sum(1 for e in all_entries if entry_status(e) == "unknow")
    know_n = sum(1 for e in all_entries if entry_status(e) == "know")
    options = [
        ("unknow", f"unknow  ({unknow_n})"),
        ("know", f"know    ({know_n})"),
        ("all", f"all     ({len(all_entries)})"),
        ("__quit__", "quit"),
    ]
    # Pre-select current filter when possible.
    start = next(
        (i for i, (oid, _) in enumerate(options) if oid == current_filter),
        0,
    )
    choice = select_menu(
        f"=== LEARN / {book} / status ===\nfilter: {current_filter}",
        options,
        sep_before={"__quit__"},
        initial_index=start,
    )
    if choice is None or choice == "__quit__":
        return None
    return choice


def render_card(
    book: str,
    entries: list,
    index: int,
    expanded: bool,
    status_filter: str,
    *,
    follow: dict | None = None,
) -> None:
    clear_screen()
    entry = entries[index]
    if follow:
        print_line(f"=== LEARN / {book} / follow ===")
    else:
        print_line(f"=== LEARN / {book} / {status_filter} ===")
    print_line(f"{index + 1} / {len(entries)}")
    print_line()
    print_line(f"num: {entry['num']}")
    print_line(f"word: {entry['word']}")

    show_detail = expanded or follow is not None
    if show_detail:
        print_line(f"phonetic: {entry.get('phonetic') or ''}")
        print_line(f"pos: {entry.get('pos') or ''}")
        print_line(f"meaning: {entry.get('meaning') or ''}")
        if follow is None:
            note = entry.get("note")
            print_line(f"note: {'' if note is None else note}")
            print_line(f"status: {entry_status(entry)}")

    print_line()
    if follow:
        mode = follow.get("mode", "en")
        times = follow.get("times", 1)
        mode_label = "english only" if mode == "en" else "english + chinese"
        print_line(f"follow: {mode_label}  x{times}")
        print_line("q quit follow")
    else:
        print_line("← prev  → next  Enter expand/collapse")
        print_line("t know  f unknow  n note  v voice  r read  q quit  s status")


def render_empty(book: str, status_filter: str) -> None:
    clear_screen()
    print_line(f"=== LEARN / {book} / {status_filter} ===")
    print_line("No words under current filter.")
    print_line()
    print_line("s status  q quit")


def note_mode(entry: dict) -> bool:
    """Open vim-like note editor. Returns True if note was saved."""
    word = entry.get("word") or ""
    saved, new_note = edit_note(word, entry.get("note"))
    if saved:
        entry["note"] = new_note
    return saved


def configure_follow_read(book: str) -> dict | None:
    """Ask follow-read options. Returns {mode, times} or None if cancelled."""
    mode = select_menu(
        f"=== LEARN / {book} / follow ===",
        [
            ("en", "english only"),
            ("both", "english + chinese"),
            ("__quit__", "quit"),
        ],
        sep_before={"__quit__"},
    )
    if mode is None or mode == "__quit__":
        return None

    times_id = select_menu(
        f"=== LEARN / {book} / follow / times ===",
        [
            ("1", "1 time"),
            ("2", "2 times"),
            ("3", "3 times"),
            ("5", "5 times"),
            ("__quit__", "quit"),
        ],
        sep_before={"__quit__"},
        initial_index=0,
    )
    if times_id is None or times_id == "__quit__":
        return None
    return {"mode": mode, "times": int(times_id)}


def run_follow_read(
    book: str,
    view: list,
    start_index: int,
    status_filter: str,
    config: dict,
) -> int:
    """Auto-advance and speak from start_index. Returns final index. q exits."""
    index = start_index
    mode = config["mode"]
    times = config["times"]

    while index < len(view):
        entry = view[index]
        render_card(
            book,
            view,
            index,
            True,
            status_filter,
            follow=config,
        )

        for _ in range(times):
            result = _speak_interruptible(entry.get("word") or "", lang="en")
            if result == "quit":
                return index
            if result == "fail":
                print_line()
                print_line("Speech unavailable (macOS say only).")
                ask_line("Press Enter to quit follow...")
                return index

            if mode == "both":
                meaning = (entry.get("meaning") or "").strip()
                if meaning:
                    if _pause_or_quit(0.25):
                        return index
                    result = _speak_interruptible(meaning, lang="zh")
                    if result == "quit":
                        return index

            if _pause_or_quit(0.35):
                return index

        index += 1
        if index >= len(view):
            break
        if _pause_or_quit(0.4):
            return index - 1

    return min(index, len(view) - 1)


def refresh_view(
    all_entries: list,
    status_filter: str,
    current: dict | None,
) -> tuple[list, int]:
    view = filter_entries(all_entries, status_filter)
    if not view:
        return view, 0
    if current is not None:
        for i, entry in enumerate(view):
            if entry is current:
                return view, i
    return view, 0


def learn_book(book: str, all_entries: list) -> None:
    status_filter = "all"
    view, index = refresh_view(all_entries, status_filter, None)
    expanded = False

    while True:
        if not view:
            render_empty(book, status_filter)
            key = read_key()
            if key["type"] == "ctrl_c":
                save_book(book, all_entries)
                sys.exit(0)
            if key["type"] != "char":
                continue
            ch = key["value"].lower()
            if ch == "q":
                save_book(book, all_entries)
                return
            if ch == "s":
                picked = change_status_filter(book, all_entries, status_filter)
                if picked is not None:
                    status_filter = picked
                    view, index = refresh_view(all_entries, status_filter, None)
                    expanded = False
                continue
            continue

        render_card(book, view, index, expanded, status_filter)
        key = read_key()

        if key["type"] == "ctrl_c":
            save_book(book, all_entries)
            sys.exit(0)
        if key["type"] == "left":
            index = (index - 1) % len(view)
            expanded = False
            continue
        if key["type"] == "right":
            index = (index + 1) % len(view)
            expanded = False
            continue
        if key["type"] == "enter":
            expanded = not expanded
            continue
        if key["type"] != "char":
            continue

        ch = key["value"].lower()
        if ch == "q":
            save_book(book, all_entries)
            return
        if ch == "t":
            current = view[index]
            current["status"] = "know"
            save_book(book, all_entries)
            view, index = refresh_view(all_entries, status_filter, current)
            expanded = False
            continue
        if ch == "f":
            current = view[index]
            current["status"] = "unknow"
            save_book(book, all_entries)
            view, index = refresh_view(all_entries, status_filter, current)
            expanded = False
            continue
        if ch == "n":
            if note_mode(view[index]):
                save_book(book, all_entries)
            continue
        if ch == "v":
            word = view[index].get("word") or ""
            if not speak_word(word):
                print_line()
                print_line("Speech unavailable (macOS say only).")
                ask_line("Press Enter to continue...")
            continue
        if ch == "r":
            config = configure_follow_read(book)
            if config is not None:
                index = run_follow_read(
                    book, view, index, status_filter, config
                )
                expanded = True
            continue
        if ch == "s":
            current = view[index]
            picked = change_status_filter(book, all_entries, status_filter)
            if picked is not None:
                status_filter = picked
                view, index = refresh_view(all_entries, status_filter, current)
                expanded = False
            continue


def _status_dot(converted: bool) -> str:
    return green("●") if converted else red("●")


def _select_md_book() -> str | None:
    """Arrow menu of md books with convert status dots.

    Returns book name, '__convert__', or None (quit).
    """
    books = list_md_books()
    if not books:
        clear_screen()
        print_line("=== LEARN ===")
        print_line()
        print_line("暂无词书。请先在 words/word_notes_md 录入 md。")
        ask_line("按 Enter 返回...")
        return None

    actions = [("__convert__", "convert"), ("__quit__", "quit")]
    options: list[tuple[str, str]] = [(name, name) for name in books] + actions
    index = 0

    while True:
        clear_screen()
        print_line("=== LEARN / select book ===")
        print_line()
        for i, (oid, label) in enumerate(options):
            if oid == "__convert__":
                print_line()
            if oid.startswith("__"):
                line = f"> {label}" if i == index else f"  {label}"
                print_line(yellow(line) if i == index else line)
                continue

            dot = _status_dot(has_json(oid))
            if i == index:
                print_line(f"{yellow('>')} {dot} {yellow(label)}")
            else:
                print_line(f"  {dot} {label}")
        print_line()

        key = read_key()
        if key["type"] == "ctrl_c" or key["type"] == "esc":
            return None
        if key["type"] == "up":
            index = (index - 1) % len(options)
            continue
        if key["type"] == "down":
            index = (index + 1) % len(options)
            continue
        if key["type"] == "enter":
            oid = options[index][0]
            if oid == "__quit__":
                return None
            return oid
        if key["type"] == "char" and key["value"].lower() == "q":
            return None


def _convert_from_learn() -> None:
    pending = list_unconverted_books()
    if not pending:
        clear_screen()
        print_line("=== LEARN / convert ===")
        print_line()
        print_line("没有未转换的词书。")
        ask_line("按 Enter 返回...")
        return

    options = [(name, name) for name in pending]
    if len(pending) > 1:
        options.append(("__all__", "all"))
    options.append(("__quit__", "quit"))
    choice = select_menu(
        "=== LEARN / convert ===\n选择要转换的 md 词书",
        options,
        sep_before={"__all__", "__quit__"},
    )
    if choice is None or choice == "__quit__":
        return

    targets = pending if choice == "__all__" else [choice]
    results = convert_books(targets)
    clear_screen()
    print_line("=== LEARN / convert ===")
    print_line()
    for book, count in results:
        print_line(f"✓ {book}.md → {book}.json ({count} 词)")
    print_line()
    ask_line("按 Enter 返回...")


def learn_mode() -> None:
    while True:
        choice = _select_md_book()
        if choice is None:
            return
        if choice == "__convert__":
            _convert_from_learn()
            continue

        book = choice
        if not has_json(book):
            clear_screen()
            print_line(f"=== LEARN / {book} ===")
            print_line()
            print_line("该词书尚未转换为 JSON。")
            print_line("请选择 convert 进行转换。")
            ask_line("按 Enter 返回...")
            continue

        all_entries = load_book(book)
        if not all_entries:
            clear_screen()
            print_line(f"=== LEARN / {book} ===")
            print_line()
            print_line("该词书为空。")
            ask_line("按 Enter 返回...")
            continue

        learn_book(book, all_entries)
        return
