#!/usr/bin/env python3
"""将 word_notes_md 中的 Markdown 表格转换为 JSON 词条文档。

支持表头：word | phonetic | POS | meaning（兼容旧版 3 列）。
JSON 字段：num / word / phonetic / pos / meaning / note / status。
转换只写 json，不覆盖源 md。

单独运行本脚本进行转换；run.py 不会自动转换。
可交互勾选要转换的词书，也可命令行指定：
  python words/md_to_json.py
  python words/md_to_json.py 9-Entertain
  python words/md_to_json.py --all
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.books import convert_books, list_md_books
from lib.ui import ask_line, clear_screen, print_line


def print_results(results: list[tuple[str, int]]) -> None:
    if not results:
        print_line("未转换任何词书。")
        return
    for book, count in results:
        print_line(f"✓ {book}.md → {book}.json ({count} 词)")


def parse_selection(raw: str, books: list[str]) -> list[str] | None:
    """Parse user input into book names. Returns None if invalid."""
    text = raw.strip().lower()
    if not text:
        return None
    if text in {"a", "all", "*"}:
        return list(books)

    selected: list[str] = []
    seen: set[str] = set()
    for part in text.replace("，", ",").split(","):
        token = part.strip()
        if not token:
            continue

        if token.isdigit():
            idx = int(token)
            if idx < 1 or idx > len(books):
                print_line(f"无效编号: {token}")
                return None
            name = books[idx - 1]
        else:
            matched = next((b for b in books if b.lower() == token), None)
            if matched is None:
                print_line(f"未找到词书: {token}")
                return None
            name = matched

        if name not in seen:
            seen.add(name)
            selected.append(name)

    return selected or None


def interactive_select() -> list[str] | None:
    books = list_md_books()
    if not books:
        print_line("未找到任何 .md 词书。")
        return None

    while True:
        clear_screen()
        print_line("========== MD → JSON ==========")
        print_line("选择要转换的词书（未选中的不会转换）：")
        print_line()
        for i, name in enumerate(books, start=1):
            print_line(f"  {i}. {name}")
        print_line()
        print_line("输入说明:")
        print_line("  a / all     - 转换全部")
        print_line("  1,3         - 按编号多选")
        print_line("  nature      - 按书名选择（可逗号分隔）")
        print_line("  q           - 退出")
        print_line()

        choice = ask_line("> ").strip().lower()
        if choice in {"q", "quit", "exit"}:
            print_line("已取消。")
            return None

        selected = parse_selection(choice, books)
        if selected is None:
            ask_line("按 Enter 继续...")
            continue

        print_line()
        print_line("将转换: " + ", ".join(selected))
        confirm = ask_line("确认? [Y/n] ").strip().lower()
        if confirm in {"", "y", "yes"}:
            return selected
        print_line("已取消本次选择。")
        ask_line("按 Enter 继续...")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="将 md 词书转换为 json")
    parser.add_argument(
        "books",
        nargs="*",
        help="要转换的词书名（不含扩展名）；省略则进入交互选择",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="转换全部 md 词书",
    )
    args = parser.parse_args(argv)

    if args.all:
        targets = list_md_books()
        if not targets:
            print_line("未找到任何 .md 词书。")
            return
        print_results(convert_books(targets))
        return

    if args.books:
        available = {b.lower(): b for b in list_md_books()}
        targets: list[str] = []
        for name in args.books:
            key = name.lower()
            if key not in available:
                print_line(f"未找到词书: {name}.md")
                return
            targets.append(available[key])
        print_results(convert_books(targets))
        return

    selected = interactive_select()
    if not selected:
        return
    print_results(convert_books(selected))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_line("\nstopped.")
        sys.exit(0)
