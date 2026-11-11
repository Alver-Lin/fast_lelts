from __future__ import annotations

from .books import highlight_matched, search_all
from .ui import ask_line, clear_screen, print_line


def format_hit(hit: dict, query: str) -> str:
    e = hit["entry"]
    word = highlight_matched(e.get("word") or "", query)
    phonetic = e.get("phonetic") or ""
    return (
        f"[{hit['book']}] #{e['num']} {word} | {phonetic} | "
        f"{e.get('pos') or ''} | {e.get('meaning') or ''} | {e.get('status') or 'unknow'}"
    )


def search_mode() -> None:
    clear_screen()
    print_line("=== SEARCH ===")
    print_line("输入单词模糊搜索；q 返回")
    print_line()

    while True:
        raw = ask_line("search> ").strip()
        if not raw:
            continue

        if raw.lower() == "q":
            return

        hits = search_all(raw)
        if hits:
            print_line(f"找到 {len(hits)} 条:")
            for hit in hits:
                print_line("  " + format_hit(hit, raw))
            continue

        print_line("词书暂无此单词")
