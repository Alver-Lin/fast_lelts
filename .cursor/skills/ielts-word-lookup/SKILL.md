---
name: ielts-word-lookup
description: >-
  Look up an English word and return fields ready for a fast_ielts word book,
  or insert/update the word into a specified book. Use when the user pastes or
  opens a fast_ielts lookup/insert request, mentions ielts-word-lookup, search
  mode finds no local entry, or asks to录入单词到词书.
---

# IELTS Word Lookup

Handle two actions from fast_ielts search mode.

## A. Lookup only

Input contains `word: <target>` and no `"action": "insert"`.

Output:

```markdown
## Lookup Result

```json
{
  "word": "...",
  "pos": "n.",
  "meaning": "...",
  "note": null,
  "status": "unknow"
}
```

### 简要说明
- 常见义项: ...
- 推荐入库义项理由: ...
```

## B. Insert into book

Input JSON includes `"action": "insert"` and `"book"`.

Steps:
1. If `pos` / `meaning` empty, fill the most common IELTS-relevant sense.
2. Update `words/word_notes_json/{book}.json`:
   - fields: `num`, `word`, `pos`, `meaning`, `note`, `status`
   - if word exists (case-insensitive) update it; else append
   - renumber `num` from 1
3. Sync `words/word_notes_md/{book}.md` table (`words | pos | meaning`).
4. Confirm with the final entry JSON.

## Rules

- Prefer the most common IELTS-relevant sense.
- `pos`: `n.`, `v.`, `adj.`, `adv.`, `phr.`, etc.
- `meaning`: concise Chinese.
- Default `note: null`, `status: "unknow"`.
