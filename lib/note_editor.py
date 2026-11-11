from __future__ import annotations

from .ui import clear_screen, print_line, read_key


def _note_to_lines(note: str | None) -> list[str]:
    if note is None or note == "":
        return [""]
    return note.split("\n")


def _lines_to_note(lines: list[str]) -> str | None:
    text = "\n".join(lines).rstrip("\n")
    if not text.strip():
        return None
    return text


def _with_cursor(line: str, col: int) -> str:
    """Render line with reverse-video cursor."""
    if not line:
        return "\033[7m \033[0m"
    col = max(0, min(col, len(line)))
    if col >= len(line):
        return line + "\033[7m \033[0m"
    return line[:col] + f"\033[7m{line[col]}\033[0m" + line[col + 1 :]


def edit_note(word: str, note: str | None) -> tuple[bool, str | None]:
    """Minimal note editor: i insert, Esc normal, :wq save&quit.

    Returns (saved, new_note). saved=False means discard changes.
    """
    lines = _note_to_lines(note)
    original = _lines_to_note(lines)
    row = 0
    col = 0
    mode = "normal"  # normal | insert | command
    cmd = ""
    hint = "i 插入  Esc 正常模式  :wq 保存退出"

    def dirty() -> bool:
        return _lines_to_note(lines) != original

    def clamp_col() -> None:
        nonlocal col
        col = max(0, min(col, len(lines[row])))

    def render(status: str = "") -> None:
        clear_screen()
        flag = " [+]" if dirty() else ""
        print_line(f"=== NOTE / {word}{flag} ===")
        if mode == "insert":
            print_line("-- INSERT --")
        elif mode == "command":
            print_line(f":{cmd}")
        else:
            print_line("-- NORMAL --")
        print_line()
        for i, line in enumerate(lines):
            prefix = f"{i + 1:>3} "
            if i == row and mode != "command":
                print_line(prefix + _with_cursor(line, col))
            else:
                print_line(prefix + (line if line else " "))
        print_line()
        print_line(status or hint)

    message = ""
    while True:
        render(message)
        message = ""
        key = read_key()

        if key["type"] == "ctrl_c":
            return False, note

        if mode == "command":
            if key["type"] == "esc":
                mode = "normal"
                cmd = ""
                continue
            if key["type"] == "backspace":
                cmd = cmd[:-1]
                continue
            if key["type"] == "enter":
                action = cmd.strip().lower()
                cmd = ""
                mode = "normal"
                if action == "wq":
                    return True, _lines_to_note(lines)
                message = f"仅支持 :wq（收到 :{action}）"
                continue
            if key["type"] == "char":
                cmd += key["value"]
            continue

        if mode == "insert":
            if key["type"] == "esc":
                mode = "normal"
                col = max(0, col - 1)
                clamp_col()
                continue
            if key["type"] == "backspace":
                if col > 0:
                    line = lines[row]
                    lines[row] = line[: col - 1] + line[col:]
                    col -= 1
                elif row > 0:
                    prev = lines[row - 1]
                    cur = lines[row]
                    col = len(prev)
                    lines[row - 1] = prev + cur
                    del lines[row]
                    row -= 1
                continue
            if key["type"] == "enter":
                line = lines[row]
                lines[row] = line[:col]
                lines.insert(row + 1, line[col:])
                row += 1
                col = 0
                continue
            if key["type"] == "left":
                col = max(0, col - 1)
                continue
            if key["type"] == "right":
                col = min(len(lines[row]), col + 1)
                continue
            if key["type"] == "up":
                row = max(0, row - 1)
                clamp_col()
                continue
            if key["type"] == "down":
                row = min(len(lines) - 1, row + 1)
                clamp_col()
                continue
            if key["type"] == "char":
                ch = key["value"]
                if ch == "\t":
                    ch = "  "
                line = lines[row]
                lines[row] = line[:col] + ch + line[col:]
                col += len(ch)
            continue

        # ---- normal mode ----
        if key["type"] in {"up", "down", "left", "right"}:
            if key["type"] == "up":
                row = max(0, row - 1)
            elif key["type"] == "down":
                row = min(len(lines) - 1, row + 1)
            elif key["type"] == "left":
                col = max(0, col - 1)
            else:
                if lines[row]:
                    col = min(len(lines[row]) - 1, col + 1)
            clamp_col()
            continue

        if key["type"] != "char":
            continue

        ch = key["value"]
        if ch == "i":
            mode = "insert"
            continue
        if ch == ":":
            mode = "command"
            cmd = ""
            continue
