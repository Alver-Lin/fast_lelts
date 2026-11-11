from __future__ import annotations

import shutil
import subprocess
import sys

from .books import (
    list_books,
    load_book,
    save_book,
)
from .note_editor import edit_note
from .ui import (
    ask_line,
    clear_screen,
    print_line,
    read_key,
    read_key_timeout,
    select_menu,
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
        print_line("q 退出跟读")
    else:
        print_line("← 上一个  → 下一个  Enter 展开/收起")
        print_line("t 认识  f 不认识  n 笔记  v 朗读  r 跟读  q 返回  s 状态")


def render_empty(book: str, status_filter: str) -> None:
    clear_screen()
    print_line(f"=== LEARN / {book} / {status_filter} ===")
    print_line("当前筛选下没有单词。")
    print_line()
    print_line("s 状态  q 返回")


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
                print_line("无法发音（仅支持 macOS 的 say）。")
                ask_line("按 Enter 退出跟读...")
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
                print_line("无法发音（仅支持 macOS 的 say）。")
                ask_line("按 Enter 继续...")
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


def learn_mode() -> None:
    books = list_books()
    if not books:
        clear_screen()
        print_line("=== LEARN ===")
        print_line()
        print_line("暂无词书。请先在 words/word_notes_md 录入 md，再运行 words/md_to_json.py 转换。")
        ask_line("按 Enter 返回...")
        return

    options = [(name, name) for name in books] + [("__quit__", "quit")]
    choice = select_menu(
        "=== LEARN / select book ===",
        options,
        sep_before={"__quit__"},
    )
    if choice is None or choice == "__quit__":
        return

    book = choice
    all_entries = load_book(book)
    if not all_entries:
        clear_screen()
        print_line(f"=== LEARN / {book} ===")
        print_line()
        print_line("该词书为空。")
        ask_line("按 Enter 返回...")
        return

    learn_book(book, all_entries)
