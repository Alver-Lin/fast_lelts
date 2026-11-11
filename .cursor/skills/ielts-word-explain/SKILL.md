---
name: ielts-word-explain
description: >-
  Generate structured IELTS vocabulary explanations for a given word entry.
  Use when the user pastes a fast_ielts explain request, mentions
  ielts-word-explain, or asks for deep analysis of a word from learn mode (m).
---

# IELTS Word Explain

When triggered, produce a full study card for the given word. Do not invent unrelated words.

## Input

Expect JSON with fields: `book`, `num`, `word`, `pos`, `meaning`, `note`, `status`.

## Output format (verbatim structure)

```markdown
# {word}

## 核心释义
- 词性: {pos}
- 中文: {meaning}
- 一句话英文释义: ...

## 用法要点
- 搭配: ...
- 语域/语气: ...
- 易错点: ...

## 例句（IELTS 向）
1. ...
2. ...
3. ...

## 近义 / 反义
- 近义: ...
- 反义: ...

## 记忆提示
...

## 可写入 note 的短摘要
（1-2 句，便于粘贴回词书 note）
```

Keep Chinese + English mixed as above. Be concise and exam-practical.
