from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MD_DIR = ROOT / "words" / "word_notes_md"
JSON_DIR = ROOT / "words" / "word_notes_json"

_BOOK_NUM_RE = re.compile(r"^(\d+)")


def ensure_dirs() -> None:
    MD_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)


def _book_sort_key(name: str) -> tuple[int, int, str]:
    """Sort numbered books by leading int (2 < 10); unnumbered last by name."""
    match = _BOOK_NUM_RE.match(name)
    if match:
        return (0, int(match.group(1)), name.lower())
    return (1, 0, name.lower())


def list_books() -> list[str]:
    ensure_dirs()
    return sorted((p.stem for p in JSON_DIR.glob("*.json")), key=_book_sort_key)


def list_md_books() -> list[str]:
    ensure_dirs()
    return sorted((p.stem for p in MD_DIR.glob("*.md")), key=_book_sort_key)


def has_json(book: str) -> bool:
    return json_path(book).exists()


def list_unconverted_books() -> list[str]:
    return [name for name in list_md_books() if not has_json(name)]


def json_path(book: str) -> Path:
    return JSON_DIR / f"{book}.json"


def md_path(book: str) -> Path:
    return MD_DIR / f"{book}.md"


def load_book(book: str) -> list[dict[str, Any]]:
    path = json_path(book)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _normalize(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, entry in enumerate(entries):
        note = entry.get("note")
        if note == "":
            note = None
        out.append(
            {
                "num": i + 1,
                "word": entry.get("word", ""),
                "phonetic": entry.get("phonetic") or "",
                "pos": entry.get("pos") or "",
                "meaning": entry.get("meaning") or "",
                "note": note,
                "status": entry.get("status") or "unknow",
            }
        )
    return out


def save_book(book: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ensure_dirs()
    normalized = _normalize(entries)
    json_path(book).write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    sync_md(book, normalized)
    return normalized


def sync_md(book: str, entries: list[dict[str, Any]]) -> None:
    rows = [
        "| word | phonetic | POS | meaning |",
        "| ---- | -------- | --- | ------- |",
    ]
    for e in entries:
        rows.append(
            f"| {e['word']} | {e.get('phonetic') or ''} | "
            f"{e.get('pos') or ''} | {e.get('meaning') or ''} |"
        )
    md_path(book).write_text("\n".join(rows) + "\n", encoding="utf-8")


def load_all_books() -> list[dict[str, Any]]:
    return [{"name": name, "entries": load_book(name)} for name in list_books()]


def levenshtein(a: str, b: str) -> int:
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        dp[i][0] = i
    for j in range(len(b) + 1):
        dp[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[-1][-1]


def fuzzy_match(query: str, word: str) -> int:
    q = query.strip().lower()
    w = word.strip().lower()
    if not q or not w:
        return 0
    if w == q:
        return 100
    if w.startswith(q):
        return 90
    if q in w:
        return 70

    qi = 0
    for ch in w:
        if qi < len(q) and ch == q[qi]:
            qi += 1
    if qi == len(q):
        return 40

    dist = levenshtein(q, w)
    max_len = max(len(q), len(w))
    ratio = 1 - dist / max_len
    return round(ratio * 50) if ratio >= 0.6 else 0


def fuzzy_match_flags(query: str, word: str) -> list[bool]:
    """Which characters in word participate in the fuzzy match (for highlight)."""
    q = query.strip().lower()
    w = word
    wl = word.lower()
    flags = [False] * len(w)
    if not q or not wl:
        return flags

    if wl == q or wl.startswith(q):
        for i in range(min(len(q), len(w))):
            flags[i] = True
        return flags

    idx = wl.find(q)
    if idx >= 0:
        for i in range(idx, idx + len(q)):
            flags[i] = True
        return flags

    qi = 0
    for i, ch in enumerate(wl):
        if qi < len(q) and ch == q[qi]:
            flags[i] = True
            qi += 1
    if qi == len(q):
        return flags

    # Levenshtein-style fallback: mark aligned equal chars via DP backtrack.
    dist = levenshtein(q, wl)
    max_len = max(len(q), len(wl))
    if max_len == 0 or 1 - dist / max_len < 0.6:
        return [False] * len(w)

    n, m = len(q), len(wl)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if q[i - 1] == wl[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)

    i, j = n, m
    while i > 0 and j > 0:
        cost = 0 if q[i - 1] == wl[j - 1] else 1
        if dp[i][j] == dp[i - 1][j - 1] + cost:
            if cost == 0:
                flags[j - 1] = True
            i -= 1
            j -= 1
        elif dp[i][j] == dp[i - 1][j] + 1:
            i -= 1
        else:
            j -= 1
    return flags


def highlight_matched(word: str, query: str) -> str:
    """ANSI-highlight characters matched by fuzzy query."""
    flags = fuzzy_match_flags(query, word)
    parts: list[str] = []
    for ch, on in zip(word, flags):
        if on:
            parts.append(f"\033[1;33m{ch}\033[0m")
        else:
            parts.append(ch)
    return "".join(parts)


def search_all(query: str, limit: int = 20) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for book in load_all_books():
        for entry in book["entries"]:
            score = fuzzy_match(query, entry.get("word", ""))
            if score > 0:
                hits.append({"book": book["name"], "entry": entry, "score": score})
    hits.sort(key=lambda h: (-h["score"], h["entry"].get("num", 0)))
    return hits[:limit]


def add_word_to_book(
    book: str,
    *,
    word: str,
    phonetic: str = "",
    pos: str = "",
    meaning: str = "",
    note: Any = None,
    status: str = "unknow",
) -> dict[str, Any]:
    entries = load_book(book)
    for entry in entries:
        if entry.get("word", "").lower() == word.lower():
            if phonetic:
                entry["phonetic"] = phonetic
            if pos:
                entry["pos"] = pos
            if meaning:
                entry["meaning"] = meaning
            if note is not None:
                entry["note"] = note
            if status:
                entry["status"] = status
            saved = save_book(book, entries)
            updated = next(e for e in saved if e["word"].lower() == word.lower())
            return {"entries": saved, "updated": True, "entry": updated}

    entries.append(
        {
            "word": word,
            "phonetic": phonetic,
            "pos": pos,
            "meaning": meaning,
            "note": note,
            "status": status,
        }
    )
    saved = save_book(book, entries)
    return {"entries": saved, "updated": False, "entry": saved[-1]}


def _header_index_map(header_cells: list[str]) -> dict[str, int]:
    """Map logical fields to column indexes from md header row."""
    aliases = {
        "word": {"word", "words"},
        "phonetic": {"phonetic", "音标", "ipa"},
        "pos": {"pos", "词性"},
        "meaning": {"meaning", "常见中文意思", "中文意思"},
    }
    index: dict[str, int] = {}
    for i, raw in enumerate(header_cells):
        key = raw.strip().lower()
        for field, names in aliases.items():
            if key in names and field not in index:
                index[field] = i
                break
    return index


def parse_md_table(content: str) -> list[dict[str, str]]:
    """Parse md table. Supports 4-col (word/phonetic/POS/meaning) and legacy 3-col."""
    lines = [ln.strip() for ln in content.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return []

    header = [c.strip() for c in lines[0].split("|")[1:-1]]
    col = _header_index_map(header)

    # Fallback by column count when header names are unrecognized.
    if "word" not in col:
        if len(header) >= 4:
            col = {"word": 0, "phonetic": 1, "pos": 2, "meaning": 3}
        elif len(header) >= 3:
            col = {"word": 0, "pos": 1, "meaning": 2}
        else:
            return []

    entries: list[dict[str, str]] = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if not cells:
            continue
        word_i = col["word"]
        if word_i >= len(cells) or not cells[word_i]:
            continue

        def cell(field: str) -> str:
            i = col.get(field)
            if i is None or i >= len(cells):
                return ""
            return cells[i]

        entries.append(
            {
                "word": cell("word"),
                "phonetic": cell("phonetic"),
                "pos": cell("pos"),
                "meaning": cell("meaning"),
            }
        )
    return entries


def convert_md_file(md_file: Path) -> tuple[str, int]:
    """Convert one md table to json, preserving note/status from existing json.

    Writes JSON only; does not overwrite the source md (keeps phonetic/layout).
    """
    ensure_dirs()
    book = md_file.stem
    parsed = parse_md_table(md_file.read_text(encoding="utf-8"))
    existing = {e["word"].lower(): e for e in load_book(book)}

    merged: list[dict[str, Any]] = []
    for row in parsed:
        old = existing.get(row["word"].lower(), {})
        merged.append(
            {
                "word": row["word"],
                "phonetic": row.get("phonetic") or "",
                "pos": row["pos"],
                "meaning": row["meaning"],
                "note": old.get("note"),
                "status": old.get("status") or "unknow",
            }
        )
    normalized = _normalize(merged)
    json_path(book).write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return book, len(normalized)


def convert_book(book: str) -> tuple[str, int]:
    path = md_path(book)
    if not path.exists():
        raise FileNotFoundError(f"未找到词书: {book}.md")
    return convert_md_file(path)


def convert_books(books: list[str] | None = None) -> list[tuple[str, int]]:
    """Convert selected md books (or all when books is None)."""
    ensure_dirs()
    targets = list_md_books() if books is None else books
    return [convert_book(name) for name in targets]


def convert_all() -> list[tuple[str, int]]:
    return convert_books(None)
