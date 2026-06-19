from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path("/Users/pengjia/EduAgent")
PY = ROOT / "outputs/20260618-highschool-physics-knowledge-v1"
JC = ROOT / "outputs/20260618-junior-chemistry-knowledge-v1"
HC = ROOT / "outputs/20260618-highschool-chemistry-knowledge-v1"

PUNCT_RE = re.compile(r"[。！？；：.!?;:]$")
SECTION_RE = re.compile(r"^【(.+?)】$")

COMMON_NOISE_PATTERNS = [
    r"^普通高中.*课程标准.*$",
    r"^义务教育\s+化学\s+课程标准.*$",
    r"^[|IⅡlD0-9 ]*义务教育\s+化学\s+课程标准.*$",
    r"^四、课程内容[|0-9Il』 ]*$",
    r"^│\s*四、课程内容\s*│$",
    r"^五、学业质量[|0-9Il』 ]*$",
    r"^│\s*五、学业质量\s*│$",
]

DROP_SENTENCE_RE = re.compile(
    r"(体会|关注|树立|增强|感受|培养|养成|态度|责任|兴趣|价值|意义|精神|信念|贡献|愿望|使命|美丽中国|绿色发展|人类文明|环保意识|安全意识|合作|审美情趣|科学自然观)"
)

TERM_HINTS = [
    "质点",
    "位移",
    "速度",
    "加速度",
    "匀变速直线运动",
    "自由落体",
    "重力",
    "弹力",
    "摩擦力",
    "胡克定律",
    "牛顿运动定律",
    "功率",
    "动能",
    "动能定理",
    "重力势能",
    "机械能守恒",
    "曲线运动",
    "平抛运动",
    "圆周运动",
    "万有引力",
    "宇宙速度",
    "相对论",
    "电场",
    "电势",
    "电容",
    "电路",
    "电流",
    "电压",
    "电阻",
    "电功",
    "电功率",
    "磁场",
    "电磁感应",
    "电磁波",
    "传感器",
    "动量",
    "冲量",
    "动量守恒",
    "简谐运动",
    "单摆",
    "机械波",
    "折射",
    "全反射",
    "干涉",
    "衍射",
    "偏振",
    "激光",
    "分子",
    "原子",
    "元素",
    "化学式",
    "化合价",
    "物质的量",
    "摩尔质量",
    "气体摩尔体积",
    "物质的量浓度",
    "氧化还原反应",
    "电离",
    "离子反应",
    "金属",
    "非金属",
    "钠",
    "铁",
    "氯",
    "氮",
    "硫",
    "化学反应",
    "质量守恒",
    "化学方程式",
    "化学平衡",
    "反应速率",
    "焓变",
    "熵变",
    "原电池",
    "电解池",
    "有机物",
    "烃",
    "官能团",
    "蛋白质",
    "糖类",
    "高分子",
    "溶液",
    "溶解度",
    "酸",
    "碱",
    "盐",
    "空气",
    "氧气",
    "二氧化碳",
    "能源",
    "材料",
    "环境",
    "健康",
    "跨学科实践",
]


def norm(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.replace(" ,", "，").replace(" .", "。")
    text = text.replace(" :", "：")
    return text.strip()


def clean_line(line: str) -> str:
    line = norm(line)
    line = line.strip("|'\"“”‘’ 』」「")
    line = re.sub(r"(?<=\d)\.\s+(?=\d)", ".", line)
    for pattern in COMMON_NOISE_PATTERNS:
        if re.match(pattern, line):
            return ""
    if re.fullmatch(r"\d{1,3}", line):
        return ""
    if re.fullmatch(r"[|0Il』 ]+", line):
        return ""
    line = re.sub(r"^例\s+(\d+)", r"例\1", line)
    line = re.sub(r"\s+：", "：", line)
    return line.strip()


def ensure_punctuation(text: str) -> str:
    text = norm(text)
    if text and not PUNCT_RE.search(text):
        text += "。"
    return text


def split_pages_from_pdftotext(path: Path) -> list[dict[str, Any]]:
    pages = path.read_text(encoding="utf-8").split("\f")
    rows: list[dict[str, Any]] = []
    for pdf_page, page in enumerate(pages, start=1):
        if not page.strip():
            continue
        visible_page: int | None = None
        raw_lines = page.splitlines()
        for raw in reversed(raw_lines):
            value = raw.strip()
            if re.fullmatch(r"\d{1,3}", value):
                visible_page = int(value)
                break
        for line_no, raw in enumerate(raw_lines, start=1):
            line = clean_line(raw)
            if not line:
                continue
            rows.append({"pdf_page": pdf_page, "book_page": visible_page, "line_no": line_no, "line": line, "ocr_confidence": ""})
    return rows


def page_confidence(base: Path, pdf_page: int) -> float | str:
    path = base / "tmp/pdf_ocr" / f"page_{pdf_page:03d}.ocr.json"
    if not path.exists():
        return ""
    items = json.loads(path.read_text(encoding="utf-8"))
    values = [float(item.get("confidence", 0)) for item in items if item.get("text")]
    return round(mean(values), 4) if values else ""


def split_pages_from_ocr(base: Path, start_page: int, end_page: int, offset: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pdf_page in range(start_page, end_page + 1):
        path = base / "tmp/pdf_text" / f"page_{pdf_page:03d}.txt"
        conf = page_confidence(base, pdf_page)
        for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = clean_line(raw)
            if not line:
                continue
            rows.append({"pdf_page": pdf_page, "book_page": pdf_page - offset, "line_no": line_no, "line": line, "ocr_confidence": conf})
    return rows


def extract_keywords(text: str, title: str = "", theme: str = "") -> str:
    source = f"{theme} {title} {text}"
    result: list[str] = []
    for term in TERM_HINTS:
        if term in source and term not in result:
            result.append(term)
    fallback = title or (theme.split("/")[-1].strip() if theme else "")
    if fallback and fallback not in result and len(fallback) <= 24:
        result.insert(0, fallback)
    if not result and theme:
        result.append(theme.split("/")[-1].strip())
    return "；".join(result[:10])


def compress_statement(text: str) -> str:
    text = re.sub(r"[（(]\s*例\s*\d+\s*[）)]", "", text)
    text = text.replace("简单的", "").replace("简单", "")
    parts = re.split(r"([，；。！？])", text)
    clauses: list[str] = []
    for index in range(0, len(parts), 2):
        clause = parts[index].strip()
        if not clause:
            continue
        if DROP_SENTENCE_RE.search(clause):
            continue
        clauses.append(clause)
    if not clauses:
        clauses = [part.strip() for part in re.split(r"[，；。！？]", text) if part.strip()]
    return ensure_punctuation("，".join(clauses))


def make_summary(subject: str, source: str, rows: list[dict[str, Any]], note: str) -> dict[str, Any]:
    return {
        "subject": subject,
        "version": "v0.1",
        "build_date": "2026-06-18",
        "source": source,
        "standard_units_count": len(rows),
        "prompt_candidates_count": len(rows),
        "note": note,
    }


def flush_unit(units: list[dict[str, Any]], current: dict[str, Any] | None, subject_code: str) -> dict[str, Any] | None:
    if not current:
        return None
    statement = ensure_punctuation("".join(current.pop("statement_parts", [])))
    if not statement:
        return None
    seq = len(units) + 1
    current["statement"] = statement
    current["keywords"] = extract_keywords(statement, current.get("item_title", ""), current.get("theme", ""))
    current["standard_unit_id"] = f"{subject_code}-STD-{seq:04d}"
    current["review_status"] = "pending_human_review"
    units.append(current)
    return None


def parse_physics_highschool() -> dict[str, Any]:
    rows = split_pages_from_pdftotext(PY / "tmp/full_text.txt")
    units: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_content = False
    section = ""
    course_category = ""
    module = ""
    theme_no = ""
    theme_title = ""
    skip_example = False

    for row in rows:
        line = row["line"]
        cat_match = re.match(r"^（[一二三]）(必修课程|选择性必修课程|选修课程)$", line)
        if cat_match:
            in_content = True
            current = flush_unit(units, current, "HSPHY")
            course_category = cat_match.group(1)
            module = ""
            theme_no = ""
            theme_title = ""
            section = ""
            continue
        module_match = re.match(r"^\d+\.\s*(必修\s*\d|选择性必修\s*\d|选修\s*\d)$", line)
        if module_match:
            current = flush_unit(units, current, "HSPHY")
            module = re.sub(r"\s+", "", module_match.group(1))
            theme_no = ""
            theme_title = ""
            section = ""
            continue
        sec_match = SECTION_RE.match(line)
        if sec_match:
            current = flush_unit(units, current, "HSPHY")
            section = sec_match.group(1)
            skip_example = False
            continue
        if not in_content:
            continue
        if re.search(r"的教学提示$|的学业要求$", line):
            current = flush_unit(units, current, "HSPHY")
            section = ""
            skip_example = False
            continue
        theme_match = re.match(r"^([1-9]\.\d+)\s+(.+)$", line)
        if theme_match and section != "内容要求":
            current = flush_unit(units, current, "HSPHY")
            theme_no = theme_match.group(1)
            theme_title = norm(theme_match.group(2))
            skip_example = False
            continue
        item_match = re.match(r"^([1-9]\.\d+\.\d+)\s+(.+)$", line)
        if item_match and section == "内容要求":
            current = flush_unit(units, current, "HSPHY")
            item_no = item_match.group(1)
            current = {
                "source_file": "高中物理课程标准（2017年版2020年修订）.pdf",
                "pdf_page": row["pdf_page"],
                "book_page": row["book_page"],
                "stage": "高中",
                "grade_min": 10,
                "grade_max": 12,
                "domain": course_category,
                "module": module,
                "theme_no": theme_no or ".".join(item_no.split(".")[:2]),
                "theme": f"{module} / {theme_title}".strip(" /"),
                "section_type": "内容要求",
                "item_no": item_no,
                "item_title": "",
                "ocr_confidence": row["ocr_confidence"],
                "statement_parts": [item_match.group(2)],
            }
            skip_example = False
            continue
        if section == "内容要求" and line.startswith("活动建议"):
            current = flush_unit(units, current, "HSPHY")
            skip_example = False
            continue
        if section == "内容要求" and re.match(r"^例\s*\d*", line):
            skip_example = True
            continue
        if current and section == "内容要求" and not skip_example:
            current["statement_parts"].append(line)
        elif current and section == "内容要求" and re.match(r"^\d+\.\d+\.\d+", line):
            skip_example = False
    return finalize_payload("physics", "高中物理", "高中物理课程标准（2017年版2020年修订）.pdf", units, "高中物理仅抽取课程内容中的内容要求；不处理好未来资料。")


def parse_chemistry_common(kind: str) -> dict[str, Any]:
    if kind == "junior":
        rows = split_pages_from_ocr(JC, 17, 43, 7)
        source_file = "义务教育化学课程标准2022.pdf"
        subject_code = "JRCHEM"
        stage = "第四学段"
        grade_min = 7
        grade_max = 9
        course_category = "义务教育化学"
        note = "义务教育化学 OCR 后仅抽取课程内容中的内容要求；不处理好未来资料。"
    else:
        rows = split_pages_from_pdftotext(HC / "tmp/full_text.txt")
        source_file = "高中化学课程标准（2017年版2020年修订）.pdf"
        subject_code = "HSCHEM"
        stage = "高中"
        grade_min = 10
        grade_max = 12
        course_category = ""
        note = "高中化学仅抽取课程内容中的内容要求；不处理好未来资料。"

    units: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_content = False
    section = ""
    module = ""
    theme_title = ""
    domain = course_category
    skip_example = False

    for row in rows:
        line = row["line"]
        if kind == "junior":
            in_content = True
        cat_match = re.match(r"^（[一二三四五]）(.+)$", line)
        if cat_match:
            in_content = True
            current = flush_unit(units, current, subject_code)
            if kind == "junior":
                domain = norm(cat_match.group(1))
                module = ""
            else:
                domain = norm(cat_match.group(1))
                module = ""
            section = ""
            theme_title = ""
            continue
        if not in_content:
            continue
        module_match = re.match(r"^(模块\s*\d+|模块\d+)\s+(.+)$", line)
        if module_match:
            current = flush_unit(units, current, subject_code)
            module = norm(f"{module_match.group(1).replace(' ', '')} {module_match.group(2)}")
            theme_title = ""
            section = ""
            continue
        series_match = re.match(r"^(系列\s*\d+|系列\d+)\s+(.+)$", line)
        if series_match:
            current = flush_unit(units, current, subject_code)
            module = norm(f"{series_match.group(1).replace(' ', '')} {series_match.group(2)}")
            theme_title = ""
            section = ""
            continue
        theme_match = re.match(r"^主题\s*(\d+)\s*[：:]\s*(.+)$", line)
        if theme_match:
            current = flush_unit(units, current, subject_code)
            theme_title = f"主题{theme_match.group(1)}：{norm(theme_match.group(2))}"
            section = ""
            continue
        sec_match = SECTION_RE.match(line)
        if sec_match:
            current = flush_unit(units, current, subject_code)
            section = sec_match.group(1)
            skip_example = False
            continue
        if section == "内容要求" and (line.startswith("【") or re.search(r"教学提示$|学业要求$", line)):
            current = flush_unit(units, current, subject_code)
            section = ""
            continue
        item_match = re.match(r"^([1-9]\.\d+(?:\.\d+)?)\s+(.+)$", line)
        if item_match and section == "内容要求":
            current = flush_unit(units, current, subject_code)
            item_no = item_match.group(1)
            title = norm(item_match.group(2))
            current = {
                "source_file": source_file,
                "pdf_page": row["pdf_page"],
                "book_page": row["book_page"],
                "stage": stage,
                "grade_min": grade_min,
                "grade_max": grade_max,
                "domain": domain,
                "module": module,
                "theme_no": re.match(r"^[1-9]", item_no).group(0) if re.match(r"^[1-9]", item_no) else "",
                "theme": " / ".join(part for part in [module, theme_title or domain] if part),
                "section_type": "内容要求",
                "item_no": item_no,
                "item_title": title,
                "ocr_confidence": row["ocr_confidence"],
                "statement_parts": [],
            }
            skip_example = False
            continue
        if current and section == "内容要求":
            if re.match(r"^例\s*\d*", line):
                skip_example = True
                continue
            if line.startswith("●"):
                current["statement_parts"].append(line.lstrip("● "))
                skip_example = False
            elif not skip_example:
                current["statement_parts"].append(line)
    subject_name = "初中化学" if kind == "junior" else "高中化学"
    return finalize_payload("chemistry", subject_name, source_file, units, note)


def finalize_payload(subject: str, display_name: str, source: str, units: list[dict[str, Any]], note: str) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for unit in units:
        statement = compress_statement(unit["statement"])
        candidates.append(
            {
                "standard_unit_id": unit["standard_unit_id"],
                "stage": unit["stage"],
                "grade_min": unit["grade_min"],
                "grade_max": unit["grade_max"],
                "domain": unit["domain"],
                "theme": unit["theme"],
                "section_type": unit["section_type"],
                "item_no": unit["item_no"],
                "pdf_page": unit["pdf_page"],
                "book_page": unit["book_page"],
                "statement": statement,
                "keywords": unit["keywords"],
            }
        )
    quality = [
        {"check": "standard_units_total", "value": len(units), "status": "info", "detail": ""},
        {"check": "prompt_candidates_total", "value": len(candidates), "status": "info", "detail": ""},
        {"check": "candidate_statement_contains_simple", "value": sum(1 for row in candidates if "简单" in row["statement"]), "status": "pass", "detail": ""},
        {"check": "candidate_statement_missing_punctuation", "value": sum(1 for row in candidates if row["statement"] and not PUNCT_RE.search(row["statement"])), "status": "pass", "detail": ""},
        {"check": "candidate_section_type_blank", "value": sum(1 for row in candidates if not row["section_type"]), "status": "pass", "detail": ""},
        {"check": "candidate_keywords_blank", "value": sum(1 for row in candidates if not row["keywords"]), "status": "info", "detail": "keywords are machine-extracted hints, not final taxonomy"},
        {"check": "units_by_domain", "value": "；".join(f"{k}:{v}" for k, v in sorted(Counter(row["domain"] for row in units).items())), "status": "info", "detail": ""},
    ]
    return {
        "summary": make_summary(subject, source, units, note) | {"display_name": display_name},
        "standard_units": units,
        "人工整理候选": candidates,
        "quality_checks": quality,
    }


def write_payload(base: Path, filename: str, payload: dict[str, Any]) -> None:
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"file": str(data_dir / filename), "standard_units": len(payload["standard_units"]), "candidates": len(payload["人工整理候选"])}, ensure_ascii=False))


def main() -> int:
    write_payload(PY, "highschool_physics_standard_data.json", parse_physics_highschool())
    write_payload(JC, "junior_chemistry_standard_data.json", parse_chemistry_common("junior"))
    write_payload(HC, "highschool_chemistry_standard_data.json", parse_chemistry_common("high"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
