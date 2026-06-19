# Knowledge Injection Prep

> 面向需要知识注入的大模型应用的知识材料准备工具。

这个目录用于集中处理“知识注入前的知识材料准备”，不要再把这类 Excel、提取中间数据和脚本散放在 EduAgent 的 `outputs/` 里。

## 目录结构

```text
knowledge-injection-prep/
  data/
    final/       最终可交付、可进入后续 RAG/Prompt 注入流程的表格
    source/      由官方标准整理出的源工作簿，保留 pdf_page/book_page 溯源字段
    reviewed/    人工验收过但不是最终版的中间版本
    archive/     历史版本和早期 source-build 归档
  docs/          制作规范、经验总结、字段说明
  scripts/       历史构建脚本和后续可复用脚本
```

## 当前最终数据

`data/final/` 下三份是当前最重要的最终成果：

- `math_canonical_labeled_v0.3.xlsx`
- `physics_canonical_labeled_v0.3.xlsx`
- `chemistry_canonical_labeled_v0.3.xlsx`

它们已经补齐：

- `canonical_label`
- `inject_policy`
- `label_group`
- `prompt_priority`
- `pdf_page`
- `book_page`

其中 `pdf_page` 和 `book_page` 来自 `data/source/` 下对应的 `mathgpt_*_knowledge_20260618*.xlsx`，通过 `standard_unit_id` 关联。

## 保留原则

- 最终交付只看 `data/final/`。
- 人工验收过程看 `data/reviewed/`。
- 追溯官方标准页码看 `data/source/`。
- 追溯早期构建过程看 `data/archive/source-builds/`。
- `.preview.png`、`.inspect.ndjson`、`.DS_Store`、大体积 OCR/tmp 过程文件默认不进入本项目。

## 脚本说明

- `scripts/20260618-science-standards-builder.py` 和 `scripts/20260618-science-workbook-builder.mjs` 是这次物理/化学阶段使用过的历史脚本。它们保留用于参考，但里面仍包含当时的路径和任务假设；以后做新学科或 IELTS 作文材料时，建议复制后按新目录结构改造，不要直接当通用框架运行。

- 文本层乱码/扫描页/提取效果差的 PDF：先把 PDF 页渲染成图片，再走 Apple Vision OCR。通过 macOS 调用 Apple Vision OCR `apple_vision_ocr.swift`。

`scripts/legacy/` 按早期 run 分目录保存了更早的数学、物理构建脚本，主要用于追溯，不建议直接运行。
