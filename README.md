# Fast IELTS

终端里的雅思词汇学习小工具：词书用 Markdown 维护，转换成 JSON 后可搜索、背词、标记掌握度，并支持朗读与跟读（macOS）。

## 功能

- **search**：跨词书模糊搜索单词
- **learn**：按词书刷卡学习
  - 展开查看音标 / 词性 / 释义 / 笔记
  - 标记 `know` / `unknow`，按状态筛选
  - `voice` 朗读，`read` 跟读
  - 内置 `convert`：把未转换的 md 转成 json

## 环境

- Python 3.10+
- 仅用标准库，无需安装第三方依赖
- 朗读 / 跟读依赖 macOS 自带的 `say`

```bash
python3 run.py
```

## 词书格式

源文件放在 `words/word_notes_md/`，Markdown 表格即可：

```markdown
| word | phonetic | POS | meaning |
| ---- | -------- | --- | ------- |
| campus | /ˈkæmpəs/ | n | 校园 |
```

也兼容中文表头：`音标` / `词性` / `常见中文意思`。

转换后的 JSON 在 `words/word_notes_json/`，字段为：

`num` · `word` · `phonetic` · `pos` · `meaning` · `note` · `status`

`status` 默认为 `unknow`，学习时可改为 `know`。

## 转换 md → json

在 **learn** 菜单里选 `convert`，或单独跑脚本：

```bash
python3 words/md_to_json.py              # 交互选择
python3 words/md_to_json.py 10-Material  # 指定词书
python3 words/md_to_json.py --all        # 全部转换
```

转换只写 json，不会覆盖源 md；已有条目的 `note` / `status` 会保留。

## Learn 快捷键

| 按键 | 作用 |
| ---- | ---- |
| ← / → | 上一个 / 下一个 |
| Enter | 展开 / 收起 |
| t | 标记 know |
| f | 标记 unknow |
| n | 编辑笔记 |
| v | 朗读（voice） |
| r | 跟读（read） |
| s | 切换状态筛选 |
| q | 退出 |

## 目录结构

```
fast_ielts/
├── run.py                 # 入口
├── lib/                   # 搜索 / 学习 / 词书逻辑
├── words/
│   ├── word_notes_md/     # 词书源文件（md）
│   ├── word_notes_json/   # 转换结果（json）
│   └── md_to_json.py      # 转换脚本
└── requirements.txt
```
