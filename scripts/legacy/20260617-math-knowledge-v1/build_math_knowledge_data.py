import json
import math
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


OUT_DIR = Path("outputs/20260617-math-knowledge-v1")
TEXT_DIR = OUT_DIR / "tmp" / "pdf_text"
OCR_DIR = OUT_DIR / "tmp" / "pdf_ocr"
DATA_DIR = OUT_DIR / "data"
MD_PATH = Path("/Users/pengjia/Downloads/数理化课程标准/数学知识点.md")
PDF_SOURCE = "义务教育数学课程标准2022.pdf"
MD_SOURCE = "数学知识点.md"
BUILD_DATE = date.today().isoformat()

STAGE_GRADES = {
    "第一学段": (1, 2),
    "第二学段": (3, 4),
    "第三学段": (5, 6),
    "第四学段": (7, 9),
}

VENDOR_STAGE_GRADES = {
    "小学": (1, 6),
    "初中": (7, 9),
    "高中": (10, 12),
}

DOMAIN_CODES = {
    "数与代数": "ALG",
    "图形与几何": "GEO",
    "统计与概率": "STA",
    "综合与实践": "INT",
}

SECTION_CODES = {
    "内容要求": "REQ",
    "学业要求": "ACH",
    "教学提示": "TIP",
}

THEME_TABLE = [
    {"domain": "数与代数", "stage": "第一学段", "grade_min": 1, "grade_max": 2, "themes": "数与运算；数量关系"},
    {"domain": "数与代数", "stage": "第二学段", "grade_min": 3, "grade_max": 4, "themes": "数与运算；数量关系"},
    {"domain": "数与代数", "stage": "第三学段", "grade_min": 5, "grade_max": 6, "themes": "数与运算；数量关系"},
    {"domain": "数与代数", "stage": "第四学段", "grade_min": 7, "grade_max": 9, "themes": "数与式；方程与不等式；函数"},
    {"domain": "图形与几何", "stage": "第一学段", "grade_min": 1, "grade_max": 2, "themes": "图形的认识与测量"},
    {"domain": "图形与几何", "stage": "第二学段", "grade_min": 3, "grade_max": 4, "themes": "图形的认识与测量；图形的位置与运动"},
    {"domain": "图形与几何", "stage": "第三学段", "grade_min": 5, "grade_max": 6, "themes": "图形的认识与测量；图形的位置与运动"},
    {"domain": "图形与几何", "stage": "第四学段", "grade_min": 7, "grade_max": 9, "themes": "图形的性质；图形的变化；图形与坐标"},
    {"domain": "统计与概率", "stage": "第一学段", "grade_min": 1, "grade_max": 2, "themes": "数据分类"},
    {"domain": "统计与概率", "stage": "第二学段", "grade_min": 3, "grade_max": 4, "themes": "数据的收集、整理与表达"},
    {"domain": "统计与概率", "stage": "第三学段", "grade_min": 5, "grade_max": 6, "themes": "数据的收集、整理与表达；随机现象发生的可能性"},
    {"domain": "统计与概率", "stage": "第四学段", "grade_min": 7, "grade_max": 9, "themes": "抽样与数据分析；随机事件的概率"},
    {"domain": "综合与实践", "stage": "第一学段", "grade_min": 1, "grade_max": 2, "themes": "主题活动"},
    {"domain": "综合与实践", "stage": "第二学段", "grade_min": 3, "grade_max": 4, "themes": "主题活动"},
    {"domain": "综合与实践", "stage": "第三学段", "grade_min": 5, "grade_max": 6, "themes": "主题活动；项目学习"},
    {"domain": "综合与实践", "stage": "第四学段", "grade_min": 7, "grade_max": 9, "themes": "项目式学习"},
]

KNOWN_THEMES = {
    "数与运算",
    "数量关系",
    "数与式",
    "方程与不等式",
    "函数",
    "图形的认识与测量",
    "图形的位置与运动",
    "图形的性质",
    "图形的变化",
    "图形与坐标",
    "数据分类",
    "数据的收集、整理与表达",
    "随机现象发生的可能性",
    "抽样与数据分析",
    "随机事件的概率",
    "主题活动",
    "项目学习",
    "项目式学习",
}

STOP_TERMS = {
    "小学",
    "初中",
    "高中",
    "数学",
    "模块",
    "基础",
    "应用",
    "综合",
    "实践",
    "年级",
    "上册",
    "下册",
    "其他",
    "无下级",
    "题型",
}

FORBIDDEN_TERMS = [
    "导数",
    "复数",
    "圆锥曲线",
    "椭圆",
    "双曲线",
    "抛物线",
    "空间向量",
    "向量法",
    "正弦定理",
    "余弦定理",
    "基本不等式",
    "数学归纳法",
    "三角恒等变换",
    "解析几何",
    "数列",
    "排列组合",
    "二项式定理",
]

ENRICHMENT_TERMS = [
    "奥数",
    "竞赛",
    "高斯",
    "同余",
    "抽屉",
    "幻方",
    "复杂数论",
    "复杂同余",
]

CORE_TERMS = [
    "百分数",
    "分数",
    "小数",
    "整数",
    "负数",
    "有理数",
    "无理数",
    "实数",
    "平方根",
    "立方根",
    "二次根式",
    "方程",
    "方程组",
    "一元一次方程",
    "一元二次方程",
    "不等式",
    "函数",
    "一次函数",
    "二次函数",
    "反比例函数",
    "三角形",
    "直角三角形",
    "等腰三角形",
    "等边三角形",
    "勾股定理",
    "逆定理",
    "全等",
    "相似",
    "平行线",
    "圆",
    "圆周角",
    "圆心角",
    "轴对称",
    "旋转",
    "平移",
    "坐标",
    "统计图",
    "平均数",
    "中位数",
    "众数",
    "方差",
    "概率",
    "随机事件",
]


def normalize_line(line: str) -> str:
    line = line.strip()
    line = line.replace("〜", "~").replace("～", "~")
    line = re.sub(r"\s+", " ", line)
    return line


def is_noise_line(line: str) -> bool:
    if not line:
        return True
    if re.fullmatch(r"[IVXLC]+", line):
        return True
    if re.fullmatch(r"\d{1,3}", line):
        return True
    if "义务教育 数学 课程标准" in line:
        return True
    if "四、课程内容" in line or line in {"课程内容", "小学部分", "初中部分"}:
        return True
    return False


def line_stage(line: str):
    compact = line.replace(" ", "")
    for stage in STAGE_GRADES:
        if compact.startswith(stage) and "年级" in compact:
            return stage
    return None


def line_domain(line: str):
    compact = line.replace(" ", "")
    for domain in DOMAIN_CODES:
        if compact.endswith(domain) and re.match(r"^（[一二三四]）", compact):
            return domain
    return None


def line_section(line: str):
    compact = line.replace(" ", "")
    for section in SECTION_CODES:
        if compact == f"【{section}】":
            return section
    return None


def line_theme(line: str):
    compact = re.sub(r"\s+", "", line)
    compact = re.sub(r"^[0-9]+[.．、]", "", compact)
    if compact in KNOWN_THEMES:
        return compact
    return None


def new_item_marker(line: str):
    compact = line.lstrip()
    patterns = [
        r"^(（\d+）)\s*(.*)$",
        r"^([①②③④⑤⑥⑦⑧⑨⑩])\s*(.*)$",
        r"^(主题活动\s*\d+\s*[:：])\s*(.*)$",
        r"^(项目学习\s*\d+\s*[:：])\s*(.*)$",
    ]
    for pattern in patterns:
        match = re.match(pattern, compact)
        if match:
            return match.group(1), match.group(2)
    return None, None


def join_statement(lines):
    text = "".join(part.strip() for part in lines if part.strip())
    text = re.sub(r"\s+", " ", text)
    text = text.replace(" .", ".")
    return text.strip()


def page_confidence(page: int) -> float:
    path = OCR_DIR / f"page_{page:03d}.ocr.json"
    if not path.exists():
        return 0.0
    observations = json.loads(path.read_text(encoding="utf-8"))
    confidences = [float(item.get("confidence", 0)) for item in observations]
    if not confidences:
        return 0.0
    return round(sum(confidences) / len(confidences), 3)


def parse_standard_units():
    units = []
    current = {
        "stage": None,
        "domain": None,
        "theme": None,
        "section": None,
    }
    active = None

    def finalize():
        nonlocal active
        if not active:
            return
        statement = join_statement(active["parts"])
        if len(statement) < 8:
            active = None
            return
        stage = active["stage"]
        grade_min, grade_max = STAGE_GRADES.get(stage, (None, None))
        domain = active["domain"] or ""
        section = active["section"] or ""
        seq = len(units) + 1
        unit_id = "MATH2022-{stage}-{domain}-{section}-{seq:04d}".format(
            stage={"第一学段": "S1", "第二学段": "S2", "第三学段": "S3", "第四学段": "S4"}.get(stage, "SX"),
            domain=DOMAIN_CODES.get(domain, "UNK"),
            section=SECTION_CODES.get(section, "SEC"),
            seq=seq,
        )
        units.append(
            {
                "standard_unit_id": unit_id,
                "source": PDF_SOURCE,
                "pdf_page": active["pdf_page"],
                "book_page": active["pdf_page"] - 7,
                "stage": stage,
                "grade_min": grade_min,
                "grade_max": grade_max,
                "domain": domain,
                "theme": active.get("theme") or "",
                "topic": active.get("topic") or active.get("theme") or "",
                "section_type": section,
                "item_no": active.get("item_no") or "",
                "statement": statement,
                "keywords": [],
                "ocr_confidence": page_confidence(active["pdf_page"]),
                "review_status": "machine_extracted",
            }
        )
        active = None

    for text_path in sorted(TEXT_DIR.glob("page_*.txt")):
        page = int(re.search(r"page_(\d+)\.txt", text_path.name).group(1))
        for raw in text_path.read_text(encoding="utf-8").splitlines():
            line = normalize_line(raw)
            if is_noise_line(line):
                continue

            stage = line_stage(line)
            if stage:
                finalize()
                current["stage"] = stage
                current["theme"] = None
                current["section"] = None
                continue

            domain = line_domain(line)
            if domain:
                finalize()
                current["domain"] = domain
                current["theme"] = None
                current["section"] = None
                continue

            section = line_section(line)
            if section:
                finalize()
                current["section"] = section
                continue

            theme = line_theme(line)
            if theme and current["section"]:
                finalize()
                current["theme"] = theme
                continue

            if not (current["stage"] and current["domain"] and current["section"]):
                continue

            marker, remainder = new_item_marker(line)
            if marker:
                finalize()
                active = {
                    "pdf_page": page,
                    "stage": current["stage"],
                    "domain": current["domain"],
                    "theme": current["theme"],
                    "topic": current["theme"],
                    "section": current["section"],
                    "item_no": marker,
                    "parts": [remainder or line],
                }
                continue

            if active is None:
                active = {
                    "pdf_page": page,
                    "stage": current["stage"],
                    "domain": current["domain"],
                    "theme": current["theme"],
                    "topic": current["theme"],
                    "section": current["section"],
                    "item_no": "",
                    "parts": [line],
                }
            else:
                active["parts"].append(line)

    finalize()
    return units


def clean_vendor_name(raw: str):
    raw = raw.strip()
    compact = re.sub(r"\s+", "", raw)
    if re.search(r"[\u4e00-\u9fff]\d+$", compact) and not re.search(r"\d+时", compact):
        cleaned = re.sub(r"\d+$", "", compact)
        return cleaned, "trailing_dataset_index_candidate"
    return compact, "none"


def infer_node_type(vendor_stage: str, clean_name: str, path_text: str):
    text = clean_name + " " + path_text
    if vendor_stage == "高中":
        return "out_of_scope"
    if any(term in text for term in FORBIDDEN_TERMS):
        return "out_of_scope"
    if any(term in text for term in ENRICHMENT_TERMS):
        return "competition_or_enrichment"
    if any(term in text for term in ["能力", "意识", "观念", "素养"]):
        return "ability"
    if any(term in text for term in ["思想", "方法", "假设法", "方程法", "配方法", "换元", "分类讨论", "反证法", "枚举", "归纳法", "数形结合", "辅助线", "设而不求"]):
        return "method"
    if any(term in text for term in ["应用题", "问题", "模块", "压轴", "题型", "情境", "情景"]):
        return "problem_type"
    return "knowledge"


def infer_domain(text: str):
    if re.search(r"统计|概率|随机|数据|平均数|方差|中位数|众数|频数|频率|样本", text):
        return "统计与概率"
    if re.search(r"三角形|四边形|多边形|圆|几何|图形|角|线段|直线|射线|平行|垂直|面积|体积|周长|轴对称|旋转|平移|坐标|勾股|相似|全等|扇形|长方体|正方体|棱柱|圆柱|圆锥", text):
        return "图形与几何"
    if re.search(r"综合|实践|项目|情境|情景|应用题|生活", text):
        return "综合与实践"
    return "数与代数"


def parse_vendor_nodes():
    nodes = []
    current_stage = None
    current_topic = None
    stack = []

    def add_node(raw_name, path, parent_id, source_line):
        clean, clean_rule = clean_vendor_name(raw_name)
        path_text = "/".join(path)
        aliases = [raw_name]
        if clean not in aliases:
            aliases.append(clean)
        node_type = infer_node_type(current_stage, clean, path_text)
        domain = infer_domain(path_text)
        seq = len(nodes) + 1
        node_id = f"TAL-MATH-{seq:05d}"
        node = {
            "vendor_node_id": node_id,
            "source": MD_SOURCE,
            "source_line": source_line,
            "vendor_stage": current_stage,
            "vendor_grade_min": VENDOR_STAGE_GRADES.get(current_stage, (None, None))[0],
            "vendor_grade_max": VENDOR_STAGE_GRADES.get(current_stage, (None, None))[1],
            "path": path,
            "path_text": "/".join(path),
            "raw_name": raw_name,
            "clean_name": clean,
            "aliases": aliases,
            "clean_rule": clean_rule,
            "node_type": node_type,
            "inferred_domain": domain,
            "parent_id": parent_id or "",
            "children_count": 0,
            "review_status": "machine_classified",
        }
        nodes.append(node)
        return node

    lines = MD_PATH.read_text(encoding="utf-8").splitlines()
    for line_no, line in enumerate(lines, 1):
        raw_line = line.rstrip()
        if raw_line.startswith("## "):
            stage = raw_line[3:].strip()
            if stage in {"小学", "初中", "高中"}:
                current_stage = stage
                current_topic = None
                stack = []
            continue
        if not current_stage:
            continue
        if raw_line.startswith("### "):
            raw_name = raw_line[4:].strip()
            current_topic = add_node(raw_name, [current_stage, raw_name], None, line_no)
            stack = [current_topic]
            continue
        match = re.match(r"^(\s*)-\s+(.+)$", raw_line)
        if not match or current_topic is None:
            continue
        raw_name = match.group(2).strip()
        if "无下级" in raw_name:
            continue
        indent = len(match.group(1).replace("\t", "  "))
        level = indent // 2 + 1
        stack = stack[:level]
        parent = stack[-1] if stack else current_topic
        path = parent["path"] + [raw_name]
        node = add_node(raw_name, path, parent["vendor_node_id"], line_no)
        stack.append(node)

    by_id = {node["vendor_node_id"]: node for node in nodes}
    for node in nodes:
        parent_id = node["parent_id"]
        if parent_id in by_id:
            by_id[parent_id]["children_count"] += 1
    return nodes


def extract_terms(text: str):
    parts = re.split(r"[/、，,；;（）()：:\s]+", text)
    terms = []
    for part in parts:
        part = part.strip()
        if len(part) < 2 or part in STOP_TERMS:
            continue
        if re.fullmatch(r"\d+", part):
            continue
        terms.append(part)
        for subpart in re.split(r"[的和与及]", part):
            if len(subpart) >= 2 and subpart not in STOP_TERMS:
                terms.append(subpart)
    for term in CORE_TERMS:
        if term in text:
            terms.append(term)
    return list(dict.fromkeys(terms))


def char_bigrams(text: str):
    compact = re.sub(r"\s+", "", text)
    if len(compact) < 2:
        return {compact} if compact else set()
    return {compact[i : i + 2] for i in range(len(compact) - 1)}


def jaccard(a: set, b: set):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def compatible_stage(vendor_stage, standard_stage):
    if vendor_stage == "小学":
        return standard_stage in {"第一学段", "第二学段", "第三学段"}
    if vendor_stage == "初中":
        return standard_stage == "第四学段"
    return False


def score_mapping(vendor, unit):
    if not compatible_stage(vendor["vendor_stage"], unit["stage"]):
        return 0.0

    clean = vendor["clean_name"]
    unit_text = f"{unit['domain']} {unit['theme']} {unit['statement']}"
    if clean and clean in unit_text and len(clean) >= 2:
        return 0.94

    terms = extract_terms(vendor["path_text"])
    hits = [term for term in terms if term in unit_text]
    if vendor["inferred_domain"] != unit["domain"] and not hits:
        return 0.0
    domain_bonus = 0.12 if vendor["inferred_domain"] == unit["domain"] else 0.0
    hit_score = min(0.36, len(hits) * 0.09)
    similarity = jaccard(char_bigrams(vendor["clean_name"]), char_bigrams(unit_text))
    path_similarity = jaccard(char_bigrams(vendor["path_text"]), char_bigrams(unit_text))
    score = 0.10 + domain_bonus + hit_score + 0.22 * similarity + 0.16 * path_similarity
    return min(score, 0.88)


def relation_for_vendor(vendor, confidence):
    node_type = vendor["node_type"]
    if node_type == "out_of_scope":
        return "out_of_scope"
    if node_type == "competition_or_enrichment":
        return "enrichment"
    if node_type == "method":
        return "method"
    if node_type == "problem_type":
        return "problem_type"
    if confidence >= 0.9:
        return "exact"
    if confidence >= 0.45:
        return "narrower"
    return "pending"


def build_mappings(vendor_nodes, standard_units):
    mappings = []
    units_by_domain = defaultdict(list)
    for unit in standard_units:
        units_by_domain[unit["domain"]].append(unit)

    for vendor in vendor_nodes:
        relation = relation_for_vendor(vendor, 0)
        if vendor["node_type"] == "out_of_scope":
            mappings.append(
                {
                    "mapping_id": f"MAP-MATH-{len(mappings) + 1:05d}",
                    "vendor_node_id": vendor["vendor_node_id"],
                    "standard_unit_id": "",
                    "knowledge_id": "",
                    "relation": "out_of_scope",
                    "confidence": 1.0,
                    "evidence": "高中节点或命中越级/高中关键词，默认不映射到义务教育课程标准。",
                    "risk": "high",
                    "review_status": "requires_human_review",
                }
            )
            continue

        candidates = standard_units
        best_unit = None
        best_score = 0.0
        for unit in candidates:
            score = score_mapping(vendor, unit)
            if score > best_score:
                best_score = score
                best_unit = unit

        if not best_unit or best_score < 0.32:
            relation = relation_for_vendor(vendor, best_score)
            mappings.append(
                {
                    "mapping_id": f"MAP-MATH-{len(mappings) + 1:05d}",
                    "vendor_node_id": vendor["vendor_node_id"],
                    "standard_unit_id": "",
                    "knowledge_id": "",
                    "relation": relation,
                    "confidence": round(best_score, 2),
                    "evidence": "未找到足够可信的同领域、同学段官方标准候选。",
                    "risk": "medium" if vendor["node_type"] in {"method", "problem_type", "competition_or_enrichment"} else "low",
                    "review_status": "pending_human_review",
                }
            )
            continue

        relation = relation_for_vendor(vendor, best_score)
        risk = "low"
        if relation in {"method", "enrichment", "out_of_scope"}:
            risk = "high"
        elif relation in {"problem_type", "pending"} or best_score < 0.6:
            risk = "medium"

        review_status = "auto_candidate" if relation in {"exact", "narrower"} and best_score >= 0.82 else "pending_human_review"
        mappings.append(
            {
                "mapping_id": f"MAP-MATH-{len(mappings) + 1:05d}",
                "vendor_node_id": vendor["vendor_node_id"],
                "standard_unit_id": best_unit["standard_unit_id"],
                "knowledge_id": "",
                "relation": relation,
                "confidence": round(best_score, 2),
                "evidence": f"MD 路径：{vendor['path_text']}；候选课标：{best_unit['stage']} / {best_unit['domain']} / {best_unit['theme']} / {best_unit['statement'][:120]}",
                "risk": risk,
                "review_status": review_status,
            }
        )
    return mappings


def enrich_standard_keywords(standard_units, vendor_nodes):
    terms = Counter()
    for node in vendor_nodes:
        clean = node["clean_name"]
        if 2 <= len(clean) <= 14 and clean not in STOP_TERMS:
            terms[clean] += 1
    term_list = [term for term, _ in terms.most_common(2000)]
    for unit in standard_units:
        statement = unit["statement"]
        found = [term for term in term_list if term in statement]
        unit["keywords"] = found[:12]


def build_canonical_nodes(vendor_nodes, standard_units, mappings):
    vendor_by_id = {node["vendor_node_id"]: node for node in vendor_nodes}
    unit_by_id = {unit["standard_unit_id"]: unit for unit in standard_units}
    canonical = {}
    for mapping in mappings:
        if mapping["relation"] not in {"exact", "narrower"}:
            continue
        if mapping["confidence"] < 0.45 or not mapping["standard_unit_id"]:
            continue
        vendor = vendor_by_id[mapping["vendor_node_id"]]
        unit = unit_by_id[mapping["standard_unit_id"]]
        key = (vendor["clean_name"], unit["domain"], unit["stage"])
        if key in canonical:
            canonical[key]["aliases"] = sorted(set(canonical[key]["aliases"]) | set(vendor["aliases"]))
            canonical[key]["related_vendor_node_ids"].append(vendor["vendor_node_id"])
            continue
        seq = len(canonical) + 1
        knowledge_id = f"K-MATH-{DOMAIN_CODES.get(unit['domain'], 'UNK')}-{seq:05d}"
        canonical[key] = {
            "knowledge_id": knowledge_id,
            "canonical_name": vendor["clean_name"],
            "aliases": vendor["aliases"],
            "subject": "math",
            "domain": unit["domain"],
            "theme": unit["theme"],
            "node_type": vendor["node_type"],
            "allowed_grade_min": unit["grade_min"],
            "allowed_grade_max": unit["grade_max"],
            "source_authority": "official_standard_candidate",
            "status": "candidate_pending_review",
            "standard_unit_id": unit["standard_unit_id"],
            "related_vendor_node_ids": [vendor["vendor_node_id"]],
            "version": "math-knowledge-v0.1",
        }
    knowledge_by_vendor = {}
    for node in canonical.values():
        for vendor_id in node["related_vendor_node_ids"]:
            knowledge_by_vendor[vendor_id] = node["knowledge_id"]
    for mapping in mappings:
        if mapping["vendor_node_id"] in knowledge_by_vendor:
            mapping["knowledge_id"] = knowledge_by_vendor[mapping["vendor_node_id"]]
    return list(canonical.values())


def build_method_boundaries(vendor_nodes):
    rows = []
    seen = set()

    def add(name, method_type, grade_min, grade_max, forbidden_before, reason, vendor_ids, status):
        key = name
        if key in seen:
            return
        seen.add(key)
        rows.append(
            {
                "method_id": f"M-MATH-{len(rows) + 1:05d}",
                "method_name": name,
                "method_type": method_type,
                "allowed_grade_min": grade_min,
                "allowed_grade_max": grade_max,
                "forbidden_before_grade": forbidden_before,
                "reason": reason,
                "related_vendor_nodes": vendor_ids,
                "review_status": status,
                "version": "math-knowledge-v0.1",
            }
        )

    for term in FORBIDDEN_TERMS:
        related = [node["vendor_node_id"] for node in vendor_nodes if term in node["path_text"]]
        add(
            term,
            "forbidden_or_high_school_method",
            10,
            12,
            10,
            "按方案先作为 1-9 年级禁用的高中/越级方法或知识；需教研最终确认。",
            related,
            "requires_human_review",
        )

    for node in vendor_nodes:
        if node["node_type"] not in {"method", "competition_or_enrichment"}:
            continue
        grade_min, grade_max = VENDOR_STAGE_GRADES.get(node["vendor_stage"], (None, None))
        forbidden_before = grade_min if node["vendor_stage"] == "高中" else None
        add(
            node["clean_name"],
            node["node_type"],
            grade_min,
            grade_max,
            forbidden_before,
            f"来源于 MD 路径：{node['path_text']}；机器分类为 {node['node_type']}，不能直接当作知识点上线。",
            [node["vendor_node_id"]],
            "pending_human_review",
        )
    return rows


def build_review_queue(vendor_nodes, standard_units, mappings):
    vendor_by_id = {node["vendor_node_id"]: node for node in vendor_nodes}
    unit_by_id = {unit["standard_unit_id"]: unit for unit in standard_units}
    rows = []
    for mapping in mappings:
        vendor = vendor_by_id[mapping["vendor_node_id"]]
        unit = unit_by_id.get(mapping["standard_unit_id"])
        if mapping["risk"] == "low" and mapping["confidence"] >= 0.82:
            continue
        rows.append(
            {
                "mapping_id": mapping["mapping_id"],
                "vendor_path": vendor["path_text"],
                "vendor_stage": vendor["vendor_stage"],
                "node_type_machine": vendor["node_type"],
                "standard_stage": unit["stage"] if unit else "",
                "standard_domain": unit["domain"] if unit else vendor["inferred_domain"],
                "standard_theme": unit["theme"] if unit else "",
                "standard_statement": unit["statement"] if unit else "",
                "source_page": unit["book_page"] if unit else "",
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
    return rows


def build_quality_checks(standard_units, vendor_nodes, mappings, canonical_nodes, method_boundaries, review_queue):
    return [
        {"check": "build_date", "value": BUILD_DATE, "note": "生成日期"},
        {"check": "standard_units_count", "value": len(standard_units), "note": "OCR 机器切分的官方标准条目"},
        {"check": "vendor_nodes_count", "value": len(vendor_nodes), "note": "MD 解析节点数，包含中间节点和叶子节点"},
        {"check": "mappings_count", "value": len(mappings), "note": "每个 MD 节点的候选映射或边界判断"},
        {"check": "canonical_nodes_count", "value": len(canonical_nodes), "note": "可进入 MathGPT 内部知识点库的候选节点，仍需审核"},
        {"check": "method_boundaries_count", "value": len(method_boundaries), "note": "方法/越级边界候选"},
        {"check": "review_queue_count", "value": len(review_queue), "note": "需要人工审核的映射/边界记录"},
        {"check": "auto_candidate_mappings", "value": sum(1 for item in mappings if item["review_status"] == "auto_candidate"), "note": "机器置信较高但仍建议抽检"},
        {"check": "high_risk_mappings", "value": sum(1 for item in mappings if item["risk"] == "high"), "note": "method/enrichment/out_of_scope 等"},
        {"check": "official_grade_source", "value": "standard_units.stage", "note": "allowed_grade_min/max 只来自课程标准学段，不来自 MD"},
        {"check": "junior_high_granularity", "value": "7-9 only", "note": "课标只给第四学段，未自动拆初一/初二/初三"},
    ]


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    standard_units = parse_standard_units()
    vendor_nodes = parse_vendor_nodes()
    enrich_standard_keywords(standard_units, vendor_nodes)
    mappings = build_mappings(vendor_nodes, standard_units)
    canonical_nodes = build_canonical_nodes(vendor_nodes, standard_units, mappings)
    method_boundaries = build_method_boundaries(vendor_nodes)
    review_queue = build_review_queue(vendor_nodes, standard_units, mappings)
    quality_checks = build_quality_checks(
        standard_units,
        vendor_nodes,
        mappings,
        canonical_nodes,
        method_boundaries,
        review_queue,
    )

    payload = {
        "summary": {
            "build_date": BUILD_DATE,
            "scope": "math only",
            "standard_source": PDF_SOURCE,
            "vendor_source": MD_SOURCE,
            "standard_units_count": len(standard_units),
            "vendor_nodes_count": len(vendor_nodes),
            "mappings_count": len(mappings),
            "canonical_nodes_count": len(canonical_nodes),
            "method_boundaries_count": len(method_boundaries),
            "review_queue_count": len(review_queue),
        },
        "stage_theme_table": THEME_TABLE,
        "standard_units": standard_units,
        "vendor_nodes": vendor_nodes,
        "knowledge_mappings": mappings,
        "canonical_knowledge_nodes": canonical_nodes,
        "method_boundaries": method_boundaries,
        "review_queue": review_queue,
        "quality_checks": quality_checks,
    }

    (DATA_DIR / "math_knowledge_data.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_jsonl(DATA_DIR / "standard_units.v0.1.jsonl", standard_units)
    write_jsonl(DATA_DIR / "vendor_nodes.v0.1.jsonl", vendor_nodes)
    write_jsonl(DATA_DIR / "knowledge_mappings.v0.1.jsonl", mappings)
    write_jsonl(DATA_DIR / "canonical_knowledge_nodes.v0.1.jsonl", canonical_nodes)
    write_jsonl(DATA_DIR / "method_boundary.v0.1.jsonl", method_boundaries)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
