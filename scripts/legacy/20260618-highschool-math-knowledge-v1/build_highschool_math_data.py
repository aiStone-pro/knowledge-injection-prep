import json
import re
import subprocess
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path("outputs/20260618-highschool-math-knowledge-v1")
TMP_DIR = ROOT / "tmp"
TEXT_DIR = TMP_DIR / "pdf_text"
DATA_DIR = ROOT / "data"
PDF_PATH = Path("/Users/pengjia/Downloads/数理化课程标准/高中数学课程标准（2017年版2020年修订）.pdf")
PDF_SOURCE = "高中数学课程标准（2017年版2020年修订）.pdf"
BUILD_DATE = date.today().isoformat()
PDF_PAGE_START = 21
PDF_PAGE_END = 81
BOOK_PAGE_OFFSET = 8

TRACK_MAP = {
    "犃": "A",
    "犅": "B",
    "犆": "C",
    "犇": "D",
    "犈": "E",
}

COURSE_CATEGORIES = ["必修课程", "选择性必修课程", "选修课程"]

VERB_PREFIXES = (
    "了解",
    "理解",
    "掌握",
    "会",
    "能",
    "能够",
    "知道",
    "认识",
    "探索",
    "通过",
    "结合",
    "经历",
    "运用",
    "体会",
    "感悟",
    "建立",
    "用",
    "发展",
)


def run_pdftotext(page: int) -> str:
    result = subprocess.run(
        [
            "pdftotext",
            "-layout",
            "-f",
            str(page),
            "-l",
            str(page),
            str(PDF_PATH),
            "-",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def normalize_text(text: str) -> str:
    for src, dst in TRACK_MAP.items():
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("", ".").replace("􀆺", "").replace("", "*")
    text = text.replace("狀", "n").replace("狓", "x").replace("犪", "a").replace("犫", "b")
    text = text.replace("犃", "A").replace("犅", "B").replace("犆", "C").replace("犇", "D").replace("犈", "E")
    text = text.replace(" ,", "，").replace(" .", "。")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def is_noise(line: str) -> bool:
    if not line:
        return True
    compact = re.sub(r"\s+", "", line)
    if compact in {"普通高中数学课程标准", "(2017年版2020年修订)", ":%&';<", "/G3A/G25/G26/G27/G3B/G3C"}:
        return True
    if re.fullmatch(r"[0-9]{1,3}", compact):
        return True
    if len(compact) <= 12 and re.fullmatch(r"[A-Za-z0-9/%&';:()!]+", compact):
        return True
    if len(compact) <= 20 and sum("\u4e00" <= ch <= "\u9fff" for ch in compact) == 0 and not any(ch in "【】" for ch in compact):
        return True
    return False


def ensure_text_pages():
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    pages = []
    for page in range(PDF_PAGE_START, PDF_PAGE_END + 1):
        out = TEXT_DIR / f"page_{page:03d}.txt"
        if not out.exists():
            out.write_text(run_pdftotext(page), encoding="utf-8")
        pages.append(out)
    return pages


def detect_course_category(line: str):
    compact = re.sub(r"\s+", "", line)
    for idx, name in [(2, "选择性必修课程"), (1, "必修课程"), (3, "选修课程")]:
        if compact == f"({['一','二','三'][idx-1]}){name}" or compact.endswith(name):
            return name
    return None


def detect_track(line: str):
    compact = re.sub(r"\s+", "", line)
    m = re.match(r"^([ABCDE])类课程$", compact)
    return m.group(1) if m else None


def detect_theme(line: str):
    compact = re.sub(r"\s+", " ", line).strip()
    m = re.match(r"^主题[一二三四五]\s*(.+)$", compact)
    if not m:
        return None
    name = m.group(1).strip()
    if len(name) > 30 or "课时" in name:
        return None
    return compact


def detect_section(line: str):
    compact = re.sub(r"\s+", "", line)
    m = re.match(r"^【(内容要求|教学提示|学业要求)】$", compact)
    return m.group(1) if m else None


def detect_unit(line: str):
    compact = re.sub(r"\s+", " ", line).strip()
    m = re.match(r"^([0-9]+)\s*[.．]\s*(.+)$", compact)
    if not m:
        return None, None
    name = m.group(2).strip("。 ")
    if len(name) > 32:
        return None, None
    if any(word in name for word in ["学分", "课程", "建议", "要求"]):
        return None, None
    return m.group(1), name


def detect_parenthesized(line: str):
    compact = line.strip()
    m = re.match(r"^[（(]\s*([0-9]+)\s*[）)]\s*(.*)$", compact)
    return (m.group(1), m.group(2).strip()) if m else (None, None)


def detect_circled(line: str):
    compact = line.strip()
    m = re.match(r"^([①②③④⑤⑥⑦⑧⑨⑩])\s*(.*)$", compact)
    if m:
        return m.group(1), m.group(2).strip()
    m = re.match(r"^([1-9])(?=[\u4e00-\u9fffA-Za-z])(.*)$", compact)
    return (m.group(1), m.group(2).strip()) if m else (None, None)


def looks_like_statement(text: str):
    if not text:
        return False
    if len(text) >= 18:
        return True
    return text.startswith(VERB_PREFIXES) or text.endswith(("。", "；", "，"))


def has_terminal_punctuation(text: str):
    return text.endswith(("。", "；", "！", "？", ".", ";", "!", "?"))


def join_parts(parts):
    text = "".join(part.strip() for part in parts if part.strip())
    text = re.sub(r"\s+", "", text)
    text = text.replace(" ,", "，").replace(" .", "。")
    text = re.sub(r"普通高中数学课程标准[（(]2017年版2020年修订[）)]", "", text)
    text = re.sub(r"\[[0-9]+\]标有\*的内容为选学内容,不作为考试要求。", "", text)
    text = re.sub(r"\[[0-9]+\]标有\*的内容为选学内容，不作为考试要求。", "", text)
    return text.strip()


def clean_prompt_statement(text: str):
    text = re.sub(r"（\s*参见案例\s*[0-9]+(?:[~～—-][0-9]+)?\s*）", "", text)
    text = re.sub(r"（\s*案例\s*[0-9]+(?:[~～—-][0-9]+)?\s*）", "", text)
    text = re.sub(r"（\s*例\s*[0-9]+(?:[~～—-][0-9]+)?\s*）", "", text)
    text = re.sub(r"例\s*[0-9]+(?:[~～—-][0-9]+)?", "", text)
    text = text.replace("简单的", "").replace("简单", "")
    text = re.sub(r"\s+", "", text).strip("，；、 ")
    if text and not has_terminal_punctuation(text):
        text += "。"
    return text


def parse_units(page_paths):
    rows = []
    context = {
        "course_category": "",
        "track": "",
        "theme": "",
        "unit": "",
        "subtopic": "",
        "section_type": "",
    }
    active = None

    def finalize():
        nonlocal active
        if not active:
            return
        statement = join_parts(active["parts"])
        active = {**active, "statement": statement}
        if len(statement) >= 3:
            idx = len(rows) + 1
            category_code = {
                "必修课程": "COMP",
                "选择性必修课程": "SEL",
                "选修课程": "ELEC",
            }.get(active["course_category"], "UNK")
            section_code = {
                "内容要求": "REQ",
                "教学提示": "TIP",
                "学业要求": "ACH",
            }.get(active["section_type"], "SEC")
            rows.append(
                {
                    "standard_unit_id": f"HSMATH2020-{category_code}-{section_code}-{idx:04d}",
                    "source": PDF_SOURCE,
                    "pdf_page": active["pdf_page"],
                    "book_page": active["pdf_page"] - BOOK_PAGE_OFFSET,
                    "course_category": active["course_category"],
                    "track": active["track"],
                    "theme": active["theme"],
                    "unit": active["unit"],
                    "subtopic": active["subtopic"],
                    "section_type": active["section_type"],
                    "item_no": active["item_no"],
                    "statement": statement,
                    "prompt_statement_candidate": clean_prompt_statement(statement),
                    "is_optional_content": "*" in " ".join([active["unit"], active["subtopic"], statement]),
                    "review_status": "machine_extracted",
                }
            )
        active = None

    def start_item(page, item_no, first_text):
        nonlocal active
        finalize()
        active = {
            "pdf_page": page,
            "course_category": context["course_category"],
            "track": context["track"],
            "theme": context["theme"],
            "unit": context["unit"],
            "subtopic": context["subtopic"],
            "section_type": context["section_type"],
            "item_no": item_no,
            "parts": [first_text] if first_text else [],
        }

    for path in page_paths:
        page = int(re.search(r"page_(\d+)\.txt", path.name).group(1))
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = normalize_text(raw)
            if is_noise(line):
                continue

            category = detect_course_category(line)
            if category:
                finalize()
                context.update({"course_category": category, "track": "", "theme": "", "unit": "", "subtopic": "", "section_type": ""})
                continue

            track = detect_track(line)
            if track:
                finalize()
                context.update({"course_category": "选修课程", "track": track, "theme": "", "unit": "", "subtopic": "", "section_type": "内容要求"})
                continue

            theme = detect_theme(line)
            if theme:
                finalize()
                context.update({"theme": theme, "unit": "", "subtopic": "", "section_type": ""})
                continue

            section = detect_section(line)
            if section:
                finalize()
                context["section_type"] = section
                context["subtopic"] = ""
                continue

            unit_no, unit_name = detect_unit(line)
            if unit_name and context["section_type"]:
                finalize()
                context["unit"] = unit_name
                context["subtopic"] = ""
                continue

            par_no, par_text = detect_parenthesized(line)
            if par_no and context["section_type"]:
                if looks_like_statement(par_text):
                    start_item(page, f"({par_no})", par_text)
                else:
                    finalize()
                    context["subtopic"] = par_text
                continue

            circled_no, circled_text = detect_circled(line)
            if circled_no and context["section_type"]:
                start_item(page, circled_no, circled_text)
                continue

            if not context["section_type"]:
                continue

            if active:
                active["parts"].append(line)
            elif context["section_type"] == "内容要求" and context["subtopic"] and looks_like_statement(line):
                start_item(page, "", line)
            elif context["section_type"] in {"教学提示", "学业要求"}:
                start_item(page, "", line)

    finalize()
    return rows


def course_structure_rows(standard_units):
    seen = set()
    rows = []
    for unit in standard_units:
        key = (
            unit["course_category"],
            unit["track"],
            unit["theme"],
            unit["unit"],
            unit["subtopic"],
        )
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "course_category": unit["course_category"],
                "track": unit["track"],
                "theme": unit["theme"],
                "unit": unit["unit"],
                "subtopic": unit["subtopic"],
            }
        )
    return rows


def prompt_rows(standard_units):
    rows = []
    for row in standard_units:
        if row["section_type"] != "内容要求":
            continue
        statement = row["prompt_statement_candidate"]
        rows.append(
            {
                "standard_unit_id": row["standard_unit_id"],
                "stage": "高中",
                "grade_min": 10,
                "grade_max": 12,
                "course_category": row["course_category"],
                "track": row["track"],
                "theme": row["theme"],
                "unit": row["unit"],
                "subtopic": row["subtopic"],
                "section_type": row["section_type"],
                "item_no": row["item_no"],
                "pdf_page": row["pdf_page"],
                "book_page": row["book_page"],
                "statement": statement,
                "source_statement": row["statement"],
                "is_optional_content": row["is_optional_content"],
                "review_status": "machine_prompt_candidate",
            }
        )
    return rows


def quality_checks(standard_units, prompt_candidates):
    section_counts = Counter(row["section_type"] for row in standard_units)
    category_counts = Counter(row["course_category"] for row in standard_units)
    prompt_blank = sum(1 for row in prompt_candidates if not row["statement"])
    prompt_simple = sum(1 for row in prompt_candidates if "简单" in row["statement"])
    prompt_example = sum(1 for row in prompt_candidates if re.search(r"例\s*[0-9]|案例\s*[0-9]", row["statement"]))
    prompt_no_punc = sum(1 for row in prompt_candidates if row["statement"] and not has_terminal_punctuation(row["statement"]))
    prompt_header_noise = sum(1 for row in prompt_candidates if "普通高中数学课程标准" in row["statement"])
    rows = [
        {"check": "build_date", "value": BUILD_DATE, "note": "生成日期"},
        {"check": "pdf_page_range", "value": f"{PDF_PAGE_START}-{PDF_PAGE_END}", "note": "高中数学课标课程内容页，书页约 13-73"},
        {"check": "standard_units_count", "value": len(standard_units), "note": "机器抽取的内容要求/教学提示/学业要求条目"},
        {"check": "prompt_candidates_count", "value": len(prompt_candidates), "note": "人工整理候选，只含内容要求"},
        {"check": "prompt_blank_statement", "value": prompt_blank, "note": "候选 statement 空值数量"},
        {"check": "prompt_contains_simple", "value": prompt_simple, "note": "候选 statement 中仍含“简单”的数量"},
        {"check": "prompt_contains_example_ref", "value": prompt_example, "note": "候选 statement 中仍含例/案例编号的数量"},
        {"check": "prompt_missing_terminal_punctuation", "value": prompt_no_punc, "note": "候选 statement 缺末尾标点数量"},
        {"check": "prompt_contains_header_noise", "value": prompt_header_noise, "note": "候选 statement 中仍含页眉噪声数量"},
    ]
    for key, value in category_counts.items():
        rows.append({"check": f"category_count:{key}", "value": value, "note": "standard_units 按课程类别计数"})
    for key, value in section_counts.items():
        rows.append({"check": f"section_count:{key}", "value": value, "note": "standard_units 按 section_type 计数"})
    return rows


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    page_paths = ensure_text_pages()
    standard_units = parse_units(page_paths)
    prompt_candidates = prompt_rows(standard_units)
    structure = course_structure_rows(standard_units)
    checks = quality_checks(standard_units, prompt_candidates)
    payload = {
        "summary": {
            "build_date": BUILD_DATE,
            "scope": "high_school_math_only",
            "source": PDF_SOURCE,
            "pdf_page_range": f"{PDF_PAGE_START}-{PDF_PAGE_END}",
            "standard_units_count": len(standard_units),
            "prompt_candidates_count": len(prompt_candidates),
            "course_structure_count": len(structure),
        },
        "standard_units": standard_units,
        "人工整理候选": prompt_candidates,
        "course_structure": structure,
        "quality_checks": checks,
    }
    (DATA_DIR / "highschool_math_knowledge_data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(DATA_DIR / "standard_units.v0.1.jsonl", standard_units)
    write_jsonl(DATA_DIR / "prompt_candidates.v0.1.jsonl", prompt_candidates)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(json.dumps({row["check"]: row["value"] for row in checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
