from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any


BASE = Path(__file__).resolve().parents[1]
PDF_TEXT_DIR = BASE / "tmp" / "pdf_text"
PDF_OCR_DIR = BASE / "tmp" / "pdf_ocr"
DATA_DIR = BASE / "data"
MD_PATH = Path("/Users/pengjia/Downloads/数理化课程标准/物理知识点.md")
SOURCE_PDF = "义务教育物理课程标准2022.pdf"
SOURCE_MD = "物理知识点.md"

CONTENT_START_PAGE = 14
CONTENT_END_PAGE = 45

DOMAIN_BY_NUM = {
    "一": "物质",
    "二": "运动和相互作用",
    "三": "能量",
    "四": "实验探究",
    "五": "跨学科实践",
}

DOMAIN_BY_PREFIX = {
    "1": "物质",
    "2": "运动和相互作用",
    "3": "能量",
    "4": "实验探究",
    "5": "跨学科实践",
}

PUNCTUATION_RE = re.compile(r"[。！？；：.!?;:]$")
EXAMPLE_REF_RE = re.compile(r"[（(]\s*例\s*\d+\s*[）)]")


def normalize_space(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.replace(" ,", "，").replace(" .", "。")
    text = text.replace("。 。", "。")
    return text.strip()


def clean_ocr_line(line: str) -> str:
    line = normalize_space(line)
    line = line.strip("|'\"“”‘’ 』』」「")
    line = re.sub(r"^四、课程内容[|0-9Il』]*$", "", line)
    line = re.sub(r"^[I|D0-9l』 ]*义务教育\s+物理\s+课程标准.*$", "", line)
    line = re.sub(r"^课程标准（2022年版）$", "", line)
    line = line.strip("|'\"“”‘’ 』』」「")
    if re.fullmatch(r"\d{1,2}", line):
        return ""
    if re.fullmatch(r"[|0Il』 ]+", line):
        return ""
    line = re.sub(r"^例\s+(\d+)", r"例\1", line)
    line = line.replace("，点", "，")
    return line.strip()


def book_page(pdf_page: int) -> int | None:
    if pdf_page >= 8:
        return pdf_page - 7
    return None


def page_confidence(pdf_page: int) -> float | None:
    path = PDF_OCR_DIR / f"page_{pdf_page:03d}.ocr.json"
    if not path.exists():
        return None
    items = json.loads(path.read_text(encoding="utf-8"))
    values = [float(item.get("confidence", 0)) for item in items if item.get("text")]
    return round(mean(values), 4) if values else None


def page_lines() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pdf_page in range(CONTENT_START_PAGE, CONTENT_END_PAGE + 1):
        path = PDF_TEXT_DIR / f"page_{pdf_page:03d}.txt"
        for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = clean_ocr_line(raw)
            if not line:
                continue
            rows.append(
                {
                    "pdf_page": pdf_page,
                    "book_page": book_page(pdf_page),
                    "line_no": line_no,
                    "line": line,
                    "page_ocr_confidence": page_confidence(pdf_page),
                }
            )
    return rows


@dataclass
class UnitBuilder:
    source_file: str = SOURCE_PDF
    pdf_page: int = 0
    book_page: int | None = None
    stage: str = "第四学段"
    grade_min: int = 7
    grade_max: int = 9
    domain: str = ""
    theme_no: str = ""
    theme: str = ""
    topic: str = ""
    section_type: str = ""
    item_no: str = ""
    statement_parts: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    page_ocr_confidence: float | None = None

    def add_statement(self, line: str) -> None:
        self.statement_parts.append(line)

    def add_example(self, line: str) -> None:
        if self.examples and not re.match(r"^例\s*\d*", line):
            self.examples[-1] = normalize_space(self.examples[-1] + line)
        else:
            self.examples.append(line)

    def to_row(self, seq: int) -> dict[str, Any] | None:
        statement = normalize_space("".join(self.statement_parts))
        if not statement:
            return None
        if not PUNCTUATION_RE.search(statement):
            statement += "。"
        return {
            "standard_unit_id": f"PHY2022-K9-STD-{seq:04d}",
            "source_file": self.source_file,
            "pdf_page": self.pdf_page,
            "book_page": self.book_page,
            "stage": self.stage,
            "grade_min": self.grade_min,
            "grade_max": self.grade_max,
            "domain": self.domain,
            "theme_no": self.theme_no,
            "theme": self.theme,
            "topic": self.topic,
            "section_type": self.section_type,
            "item_no": self.item_no,
            "statement": statement,
            "examples": "；".join(self.examples),
            "keywords": "、".join(extract_keywords(statement)),
            "ocr_confidence": self.page_ocr_confidence,
            "review_status": "pending_human_review",
        }


def extract_keywords(text: str) -> list[str]:
    candidates = [
        "物态变化",
        "温度计",
        "质量",
        "密度",
        "分子",
        "原子",
        "宇宙",
        "机械运动",
        "分子热运动",
        "速度",
        "力",
        "重力",
        "弹力",
        "摩擦力",
        "牛顿第一定律",
        "压强",
        "浮力",
        "杠杆",
        "滑轮",
        "声",
        "光",
        "反射",
        "折射",
        "平面镜",
        "凸透镜",
        "电荷",
        "电路",
        "电流",
        "电压",
        "电阻",
        "欧姆定律",
        "电功",
        "电功率",
        "磁",
        "电磁感应",
        "能量",
        "机械能",
        "内能",
        "热值",
        "比热容",
        "能源",
        "可持续发展",
        "实验探究",
        "跨学科实践",
    ]
    seen: list[str] = []
    for term in candidates:
        if term in text and term not in seen:
            seen.append(term)
    return seen[:12]


def parse_standard_units() -> list[dict[str, Any]]:
    rows = page_lines()
    units: list[dict[str, Any]] = []
    current: UnitBuilder | None = None
    current_domain = ""
    current_theme_no = ""
    current_theme = ""
    current_section = ""
    teaching_group = ""
    capturing_example = False

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        row = current.to_row(len(units) + 1)
        if row:
            units.append(row)
        current = None

    def start(row: dict[str, Any], section_type: str, item_no: str, first_line: str, topic: str = "") -> None:
        nonlocal current, capturing_example
        flush()
        current = UnitBuilder(
            pdf_page=int(row["pdf_page"]),
            book_page=row["book_page"],
            domain=current_domain,
            theme_no=current_theme_no,
            theme=current_theme,
            topic=topic or teaching_group or current_theme,
            section_type=section_type,
            item_no=item_no,
            page_ocr_confidence=row["page_ocr_confidence"],
        )
        current.add_statement(first_line)
        capturing_example = False

    for row in rows:
        line = str(row["line"])
        domain_match = re.match(r"^（([一二三四五])）(.+)$", line)
        if domain_match and DOMAIN_BY_NUM.get(domain_match.group(1)):
            flush()
            current_domain = DOMAIN_BY_NUM[domain_match.group(1)]
            current_theme_no = ""
            current_theme = ""
            current_section = ""
            teaching_group = ""
            capturing_example = False
            continue

        if line in {"【内容要求】", "【学业要求】", "【教学提示】"}:
            flush()
            current_section = line.strip("【】")
            teaching_group = ""
            capturing_example = False
            continue

        topic_match = re.match(r"^([1-5]\.\d+)\s+(.+)$", line)
        if topic_match:
            flush()
            current_theme_no = topic_match.group(1)
            current_theme = normalize_space(topic_match.group(2))
            if not current_domain:
                current_domain = DOMAIN_BY_PREFIX.get(current_theme_no[0], "")
            if current_section == "活动建议":
                current_section = "内容要求"
            teaching_group = ""
            capturing_example = False
            continue

        item_match = re.match(r"^([1-5]\.\d+\.\d+)\s+(.+)$", line)
        if item_match:
            item_no = item_match.group(1)
            if not current_domain:
                current_domain = DOMAIN_BY_PREFIX.get(item_no[0], "")
            if not current_theme_no or not item_no.startswith(current_theme_no + "."):
                current_theme_no = ".".join(item_no.split(".")[:2])
            start(row, current_section or "内容要求", item_no, item_match.group(2), topic=current_theme)
            continue

        if line == "活动建议：":
            flush()
            current_section = "活动建议"
            capturing_example = False
            continue

        teaching_group_match = re.match(r"^（([12])）(.+建议)$", line)
        if current_section == "教学提示" and teaching_group_match:
            flush()
            teaching_group = teaching_group_match.group(2)
            capturing_example = False
            continue

        marker_match = re.match(r"^（(\d+)）\s*(.+)$", line)
        if marker_match and current_section in {"学业要求", "活动建议"}:
            start(row, current_section, marker_match.group(1), marker_match.group(2), topic=current_theme)
            continue

        bullet_match = re.match(r"^([①②③④⑤⑥⑦⑧⑨⑩])(.+)$", line)
        if bullet_match and current_section == "教学提示":
            start(row, current_section, bullet_match.group(1), bullet_match.group(2), topic=teaching_group)
            continue

        example_match = re.match(r"^例\s*\d*\s*(.+)$", line)
        if example_match and current is not None and current_section in {"内容要求", "活动建议"}:
            current.add_example(line)
            capturing_example = True
            continue

        if current is not None:
            if capturing_example:
                current.add_example(line)
            else:
                current.add_statement(line)
            continue

        if current_section == "教学提示" and line and len(line) >= 8:
            start(row, current_section, "intro", line, topic=teaching_group or "教学提示")

    flush()
    return units


def clean_vendor_name(name: str) -> tuple[str, list[str], str]:
    raw = normalize_space(name)
    clean = re.sub(r"（无下级，作为独立知识点/解题思想标签）", "", raw).strip()
    clean = re.sub(r"(?<!\d)([一-龥A-Za-z）)])(\d{1,2})$", r"\1", clean)
    aliases = [raw]
    if clean and clean != raw:
        aliases.append(clean)
        rule = "trailing_dataset_index_candidate"
    else:
        rule = "none"
    return clean or raw, list(dict.fromkeys(aliases)), rule


def classify_node(stage: str, path: list[str], name: str) -> str:
    joined = "/".join(path + [name])
    if stage == "高中":
        return "out_of_scope"
    if re.search(r"压轴题|实验题|常识题|阅读题|设计实验题|读数题|综合题|问题$", name):
        return "problem_type"
    if re.search(r"方法|思想|整体法|隔离法|控制变量|转换法|等效|类比|观察法|放大法|模型法|流向法|理想实验法|分析法", joined):
        return "method"
    if re.search(r"观念|态度|责任|本质|推理|论证|交流|解释|证据|质疑|创新|意识|能力", name):
        return "ability"
    if "（无下级" in name:
        return "problem_type"
    return "knowledge"


def infer_vendor_domain(path: list[str], name: str) -> str:
    joined = "/".join(path + [name])
    if re.search(r"物态|密度|质量|分子|原子|材料|物质", joined):
        return "物质"
    if re.search(r"声|光|力|运动|压强|浮力|杠杆|滑轮|电路|电流|电压|电阻|欧姆|磁|电荷|透镜|平面镜", joined):
        return "运动和相互作用"
    if re.search(r"能量|功|功率|机械效率|机械能|内能|热值|比热容|能源|电功", joined):
        return "能量"
    if re.search(r"实验|探究|测量|读数|控制变量|转换法|观察法", joined):
        return "实验探究"
    if re.search(r"科学态度|社会责任|科普|生活|工程|社会发展|安全|低碳", joined):
        return "跨学科实践"
    return ""


def parse_vendor_nodes() -> list[dict[str, Any]]:
    lines = MD_PATH.read_text(encoding="utf-8").splitlines()
    nodes: list[dict[str, Any]] = []
    stage = ""
    stack: dict[int, str] = {}
    last_node_index: int | None = None

    def add_node(raw_name: str, depth: int) -> None:
        nonlocal last_node_index
        clean_name, aliases, clean_rule = clean_vendor_name(raw_name)
        stack[depth] = clean_name
        for key in list(stack.keys()):
            if key > depth:
                del stack[key]
        path = [stage] + [stack[i] for i in sorted(stack) if i <= depth]
        node_type = classify_node(stage, path[:-1], raw_name)
        nodes.append(
            {
                "vendor_node_id": f"TAL-PHY-{len(nodes) + 1:04d}",
                "source_file": SOURCE_MD,
                "vendor_stage": stage,
                "path": " / ".join(path),
                "raw_name": raw_name,
                "clean_name": clean_name,
                "aliases": "；".join(aliases),
                "clean_rule": clean_rule,
                "depth": depth,
                "node_type": node_type,
                "inferred_domain": infer_vendor_domain(path[:-1], clean_name),
                "children_count": 0,
                "review_status": "pending_human_review" if node_type != "out_of_scope" else "out_of_scope_for_k9",
            }
        )
        last_node_index = len(nodes) - 1

    for raw in lines:
        if not raw.strip() or raw.startswith("# ") or raw.startswith(">") or raw.startswith("|"):
            continue
        stage_match = re.match(r"^##\s+(小学|初中|高中)$", raw)
        if stage_match:
            stage = stage_match.group(1)
            stack = {}
            last_node_index = None
            continue
        if not stage or stage == "小学":
            continue
        h3_match = re.match(r"^###\s+(.+)$", raw)
        if h3_match:
            add_node(h3_match.group(1).strip(), 1)
            continue
        bullet_match = re.match(r"^(\s*)-\s+(.+)$", raw)
        if bullet_match:
            depth = 2 + len(bullet_match.group(1)) // 2
            add_node(bullet_match.group(2).strip(), depth)
            continue
        if last_node_index is not None and raw.strip().startswith("（"):
            addition = raw.strip()
            nodes[last_node_index]["raw_name"] = normalize_space(nodes[last_node_index]["raw_name"] + addition)
            clean_name, aliases, clean_rule = clean_vendor_name(nodes[last_node_index]["raw_name"])
            nodes[last_node_index]["clean_name"] = clean_name
            nodes[last_node_index]["aliases"] = "；".join(aliases)
            nodes[last_node_index]["clean_rule"] = clean_rule
            path_parts = nodes[last_node_index]["path"].split(" / ")
            path_parts[-1] = clean_name
            nodes[last_node_index]["path"] = " / ".join(path_parts)

    node_paths = [node["path"] for node in nodes]
    for node in nodes:
        prefix = node["path"] + " / "
        node["children_count"] = sum(1 for path in node_paths if path.startswith(prefix))
    return nodes


COMMON_STOP = {
    "认识",
    "了解",
    "知道",
    "描述",
    "说明",
    "举例",
    "列举",
    "运用",
    "通过",
    "实验",
    "探究",
    "观察",
    "测量",
    "理解",
    "概念",
    "计算",
    "判断",
    "应用",
    "特点",
    "基本",
    "相关",
    "关系",
    "问题",
    "方法",
    "现象",
    "因素",
    "大小",
    "比较",
    "辨析",
    "定义",
    "及其",
}


def significant_terms(text: str) -> set[str]:
    text = re.sub(r"[，。；：、（）()“”《》/\\\-\s]", "", text)
    terms: set[str] = set()
    for size in (2, 3, 4, 5, 6):
        for i in range(0, max(0, len(text) - size + 1)):
            term = text[i : i + size]
            if term in COMMON_STOP:
                continue
            if any(stop == term for stop in COMMON_STOP):
                continue
            terms.add(term)
    return terms


def compact_name_for_match(name: str) -> str:
    text = re.sub(r"(的)?(概念|理解|定义|认识|判断|应用|计算|比较|辨析|特点|方法|实验|探究|问题|基础|简单|综合)$", "", name)
    text = re.sub(r"^(探究|认识|判断|了解|用|测量)", "", text)
    return text.strip()


def score_vendor_to_standard(node: dict[str, Any], unit: dict[str, Any]) -> float:
    name = node["clean_name"]
    compact = compact_name_for_match(name)
    target = " ".join(
        [
            str(unit.get("domain", "")),
            str(unit.get("theme", "")),
            str(unit.get("statement", "")),
            str(unit.get("examples", "")),
        ]
    )
    score = 0.0
    if name and name in target:
        score += 0.72
    elif compact and len(compact) >= 2 and compact in target:
        score += 0.58
    name_terms = significant_terms(compact or name)
    target_terms = significant_terms(target)
    if name_terms and target_terms:
        overlap = len(name_terms & target_terms) / max(1, min(len(name_terms), len(target_terms)))
        score += min(0.45, overlap * 0.45)
    if node.get("inferred_domain") and node.get("inferred_domain") == unit.get("domain"):
        score += 0.18
    elif node.get("inferred_domain") and node.get("inferred_domain") != unit.get("domain"):
        score -= 0.08
    if unit.get("theme") and compact and compact[:2] in str(unit.get("theme")):
        score += 0.06
    return max(0.0, min(0.99, round(score, 4)))


def relation_for(node: dict[str, Any], best_score: float) -> tuple[str, str, str]:
    node_type = node["node_type"]
    if node["vendor_stage"] == "高中":
        return "out_of_scope", "high", "requires_human_review"
    if node_type == "method":
        return "method", "medium", "requires_human_review"
    if node_type == "problem_type":
        return "problem_type", "medium", "requires_human_review"
    if node_type == "ability":
        return "broader", "medium", "requires_human_review"
    if best_score >= 0.9:
        return "exact", "low", "auto_candidate"
    if best_score >= 0.72:
        return "narrower", "low", "auto_candidate"
    if best_score >= 0.55:
        return "pending", "medium", "pending_human_review"
    return "pending", "high", "pending_human_review"


def build_mappings(vendor_nodes: list[dict[str, Any]], standard_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    content_units = [unit for unit in standard_units if unit["section_type"] == "内容要求"]
    mappings: list[dict[str, Any]] = []
    for node in vendor_nodes:
        if node["vendor_stage"] == "高中":
            mappings.append(
                {
                    "mapping_id": f"MAP-PHY-{len(mappings) + 1:05d}",
                    "vendor_node_id": node["vendor_node_id"],
                    "vendor_path": node["path"],
                    "standard_unit_id": "",
                    "standard_statement": "",
                    "standard_domain": "",
                    "standard_theme": "",
                    "relation": "out_of_scope",
                    "confidence": 1.0,
                    "risk": "high",
                    "evidence": "好未来节点属于高中学段；义务教育物理 7-9 年级默认不可使用，保留为越级黑名单候选。",
                    "review_status": "requires_human_review",
                    "candidate_rank": "",
                    "candidate_2": "",
                    "candidate_3": "",
                }
            )
            continue
        scored = sorted(
            ((score_vendor_to_standard(node, unit), unit) for unit in content_units),
            key=lambda pair: pair[0],
            reverse=True,
        )
        top = scored[:3]
        best_score, best_unit = top[0] if top else (0.0, None)
        relation, risk, review_status = relation_for(node, best_score)
        evidence = "机器候选："
        if best_unit:
            evidence += f"MD 路径为“{node['path']}”；课标候选为“{best_unit['domain']} / {best_unit['theme']} / {best_unit['statement']}”。"
        else:
            evidence += f"MD 路径为“{node['path']}”；未召回有效课标候选。"
        mappings.append(
            {
                "mapping_id": f"MAP-PHY-{len(mappings) + 1:05d}",
                "vendor_node_id": node["vendor_node_id"],
                "vendor_path": node["path"],
                "standard_unit_id": best_unit["standard_unit_id"] if best_unit else "",
                "standard_statement": best_unit["statement"] if best_unit else "",
                "standard_domain": best_unit["domain"] if best_unit else "",
                "standard_theme": best_unit["theme"] if best_unit else "",
                "relation": relation,
                "confidence": best_score,
                "risk": risk,
                "evidence": evidence,
                "review_status": review_status,
                "candidate_rank": "1" if best_unit else "",
                "candidate_2": format_candidate(top[1]) if len(top) > 1 else "",
                "candidate_3": format_candidate(top[2]) if len(top) > 2 else "",
            }
        )
    return mappings


def format_candidate(pair: tuple[float, dict[str, Any]]) -> str:
    score, unit = pair
    return f"{score:.2f} | {unit['standard_unit_id']} | {unit['domain']} / {unit['theme']} | {unit['statement']}"


def prompt_statement(statement: str) -> str:
    text = statement
    text = EXAMPLE_REF_RE.sub("", text)
    text = text.replace("简单的", "").replace("简单", "")
    text = normalize_space(text)
    if not PUNCTUATION_RE.search(text):
        text += "。"
    return text


def build_human_candidates(standard_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for unit in standard_units:
        if unit["section_type"] != "内容要求":
            continue
        statement = prompt_statement(unit["statement"])
        rows.append(
            {
                "candidate_id": f"PHY-K9-PROMPT-{len(rows) + 1:04d}",
                "standard_unit_id": unit["standard_unit_id"],
                "stage": unit["stage"],
                "grade_min": unit["grade_min"],
                "grade_max": unit["grade_max"],
                "domain": unit["domain"],
                "theme_no": unit["theme_no"],
                "theme": unit["theme"],
                "item_no": unit["item_no"],
                "statement": statement,
                "source_statement": unit["statement"],
                "source_examples": unit["examples"],
                "pdf_page": unit["pdf_page"],
                "book_page": unit["book_page"],
                "review_status": "pending_user_review",
                "human_statement": "",
            }
        )
    return rows


def build_canonical_nodes(standard_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for unit in standard_units:
        if unit["section_type"] != "内容要求":
            continue
        nodes.append(
            {
                "knowledge_id": f"K-PHY-K9-{len(nodes) + 1:04d}",
                "canonical_name": f"{unit['theme_no']} {unit['theme']} / {unit['item_no']}",
                "aliases": "；".join(extract_keywords(unit["statement"])),
                "subject": "physics",
                "domain": unit["domain"],
                "theme": unit["theme"],
                "node_type": "knowledge",
                "allowed_grade_min": 7,
                "allowed_grade_max": 9,
                "source_authority": "official_standard",
                "standard_unit_id": unit["standard_unit_id"],
                "status": "draft_candidate",
                "version": "v0.1",
            }
        )
    return nodes


def build_method_boundaries(vendor_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in vendor_nodes:
        if node["vendor_stage"] == "高中":
            rows.append(
                {
                    "method_id": f"PHY-MB-{len(rows) + 1:04d}",
                    "method_name": node["clean_name"],
                    "method_type": "knowledge_or_method_out_of_scope",
                    "allowed_grade_min": 10,
                    "allowed_grade_max": 12,
                    "forbidden_before_grade": 10,
                    "reason": "来源为高中物理知识点树，义务教育 7-9 年级普通答题默认禁止使用。",
                    "related_vendor_node_id": node["vendor_node_id"],
                    "vendor_path": node["path"],
                    "review_status": "requires_human_review",
                    "version": "v0.1",
                }
            )
        elif node["node_type"] == "method":
            rows.append(
                {
                    "method_id": f"PHY-MB-{len(rows) + 1:04d}",
                    "method_name": node["clean_name"],
                    "method_type": "junior_method_or_strategy",
                    "allowed_grade_min": 7,
                    "allowed_grade_max": 9,
                    "forbidden_before_grade": "",
                    "reason": "机构节点被机器识别为方法或策略，不直接作为知识白名单；需教研确认使用边界。",
                    "related_vendor_node_id": node["vendor_node_id"],
                    "vendor_path": node["path"],
                    "review_status": "requires_human_review",
                    "version": "v0.1",
                }
            )
    return rows


def build_review_queue(
    mappings: list[dict[str, Any]],
    vendor_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    priority = {"high": 1, "medium": 2, "low": 3}
    for mapping in mappings:
        if mapping["review_status"] == "auto_candidate" and mapping["risk"] == "low":
            continue
        node = vendor_by_id.get(mapping["vendor_node_id"], {})
        rows.append(
            {
                "review_id": f"PHY-REVIEW-{len(rows) + 1:04d}",
                "priority": priority.get(mapping["risk"], 9),
                "vendor_node_id": mapping["vendor_node_id"],
                "vendor_stage": node.get("vendor_stage", ""),
                "vendor_path": mapping["vendor_path"],
                "node_type_machine": node.get("node_type", ""),
                "standard_unit_id": mapping["standard_unit_id"],
                "standard_domain": mapping["standard_domain"],
                "standard_theme": mapping["standard_theme"],
                "standard_statement": mapping["standard_statement"],
                "relation_machine": mapping["relation"],
                "confidence": mapping["confidence"],
                "risk": mapping["risk"],
                "reviewer_relation": "",
                "reviewer_grade_min": "",
                "reviewer_grade_max": "",
                "reviewer_note": "",
                "decision": "",
            }
        )
    return sorted(rows, key=lambda row: (row["priority"], row["vendor_stage"], row["vendor_path"]))


def build_quality_checks(
    standard_units: list[dict[str, Any]],
    human_candidates: list[dict[str, Any]],
    vendor_nodes: list[dict[str, Any]],
    mappings: list[dict[str, Any]],
    method_boundaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(name: str, value: Any, status: str = "info", detail: str = "") -> None:
        checks.append({"check": name, "value": value, "status": status, "detail": detail})

    add("standard_units_total", len(standard_units))
    add("standard_units_content_requirements", sum(1 for row in standard_units if row["section_type"] == "内容要求"))
    add("human_candidates_total", len(human_candidates))
    add("vendor_nodes_total", len(vendor_nodes))
    add("knowledge_mappings_total", len(mappings))
    add("method_boundaries_total", len(method_boundaries))
    add("candidate_statement_contains_simple", sum(1 for row in human_candidates if "简单" in row["statement"]), "pass")
    add(
        "candidate_statement_missing_punctuation",
        sum(1 for row in human_candidates if not PUNCTUATION_RE.search(row["statement"])),
        "pass",
    )
    add(
        "candidate_statement_example_ref",
        sum(1 for row in human_candidates if EXAMPLE_REF_RE.search(row["statement"])),
        "pass",
    )
    add("standard_units_empty_statement", sum(1 for row in standard_units if not row["statement"]), "pass")
    add(
        "standard_units_by_section",
        "；".join(f"{key}:{value}" for key, value in sorted(Counter(row["section_type"] for row in standard_units).items())),
    )
    add(
        "standard_units_by_domain",
        "；".join(f"{key}:{value}" for key, value in sorted(Counter(row["domain"] for row in standard_units).items())),
    )
    add(
        "vendor_nodes_by_stage",
        "；".join(f"{key}:{value}" for key, value in sorted(Counter(row["vendor_stage"] for row in vendor_nodes).items())),
    )
    add(
        "vendor_nodes_by_type",
        "；".join(f"{key}:{value}" for key, value in sorted(Counter(row["node_type"] for row in vendor_nodes).items())),
    )
    add(
        "mappings_by_relation",
        "；".join(f"{key}:{value}" for key, value in sorted(Counter(row["relation"] for row in mappings).items())),
    )
    confidence_values = [row["ocr_confidence"] for row in standard_units if row.get("ocr_confidence") is not None]
    add("ocr_confidence_min", min(confidence_values) if confidence_values else "")
    add("ocr_confidence_avg", round(mean(confidence_values), 4) if confidence_values else "")
    return checks


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    standard_units = parse_standard_units()
    vendor_nodes = parse_vendor_nodes()
    mappings = build_mappings(vendor_nodes, standard_units)
    human_candidates = build_human_candidates(standard_units)
    canonical_nodes = build_canonical_nodes(standard_units)
    method_boundaries = build_method_boundaries(vendor_nodes)
    vendor_by_id = {row["vendor_node_id"]: row for row in vendor_nodes}
    review_queue = build_review_queue(mappings, vendor_by_id)
    quality_checks = build_quality_checks(standard_units, human_candidates, vendor_nodes, mappings, method_boundaries)

    payload = {
        "metadata": {
            "subject": "physics",
            "version": "v0.1",
            "source_pdf": SOURCE_PDF,
            "source_md": SOURCE_MD,
            "content_pdf_page_range": f"{CONTENT_START_PAGE}-{CONTENT_END_PAGE}",
            "book_page_offset": "book_page = pdf_page - 7",
            "notes": "OCR text extracted from scanned PDF with Apple Vision; grade range is official义务教育物理整体 7-9, not single-grade sequencing.",
        },
        "standard_units": standard_units,
        "vendor_nodes": vendor_nodes,
        "knowledge_mappings": mappings,
        "canonical_knowledge_nodes": canonical_nodes,
        "method_boundaries": method_boundaries,
        "人工整理候选": human_candidates,
        "review_queue": review_queue,
        "quality_checks": quality_checks,
    }
    (DATA_DIR / "physics_knowledge_data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(DATA_DIR / "standard_units.jsonl", standard_units)
    write_jsonl(DATA_DIR / "vendor_nodes.jsonl", vendor_nodes)
    write_jsonl(DATA_DIR / "knowledge_mappings.jsonl", mappings)
    write_jsonl(DATA_DIR / "canonical_knowledge_nodes.jsonl", canonical_nodes)
    write_jsonl(DATA_DIR / "method_boundaries.jsonl", method_boundaries)
    write_jsonl(DATA_DIR / "human_candidates.jsonl", human_candidates)
    write_jsonl(DATA_DIR / "review_queue.jsonl", review_queue)
    print(json.dumps({"standard_units": len(standard_units), "vendor_nodes": len(vendor_nodes), "mappings": len(mappings), "human_candidates": len(human_candidates)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
