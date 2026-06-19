# 用于大模型知识注入的资料整理方法

生成日期：2026-06-18

## 目标

把官方标准、评分标准、专家模板、课程标准等资料，整理成大模型能稳定理解、后端能确定性过滤、产品经理能人工 review 的结构化知识表。

这套方法适用于两类场景：

- MathGPT：按学段、学科、知识方法边界注入，防止越级解法。
- RedPen：按 IELTS 目标分数段、题型、评分维度注入考官模板和反馈标准。

核心原则是：先把官方材料保留为可追溯原文，再用大模型能力把每条原文压缩成短标签，最后由人工 review 标签，而不是让产品经理逐条提炼专业知识点。

## 总体流程

1. 收集官方标准和权威资料。
2. 抽取最小可 review 单元。
3. 生成基础 Excel。
4. 阅读每条 statement，用大模型能力总结 `canonical_label` 和 `inject_policy`。
5. 人工 review 标签。
6. 程序化补充 `label_group` 和 `prompt_priority`。
7. 按用户选择条件生成 prompt 知识包。

其中第 4 步不能用正则、关键词匹配或机器学习聚类替代。它需要理解 statement 的教育含义或评分含义。

## 基础 Excel 字段

推荐所有知识源先整理成同一种审阅表：

| 字段 | 必填 | 含义 |
| --- | --- | --- |
| `standard_unit_id` | 是 | 稳定唯一 ID。不要依赖行号。 |
| `subject` | 是 | 知识所属产品域或学科，例如 `math`、`physics`、`chemistry`、`ielts_writing`。 |
| `stage_bucket` | 是 | 粗粒度适用阶段，例如 `第一学段`、`第四学段`、`高中`、`IELTS Band 6`。 |
| `grade_min` | 视场景 | MathGPT 可填年级下限。RedPen 可为空或填目标 band 下限。 |
| `grade_max` | 视场景 | MathGPT 可填年级上限。RedPen 可为空或填目标 band 上限。 |
| `domain` | 是 | 一级分类，例如 `函数`、`力学`、`Task Response`。 |
| `theme` | 是 | 二级主题，例如 `三角恒等变换`、`Cohesion and Coherence`。 |
| `pdf_page` | 是 | 参考的官方标准PDF文件的页数索引，方便review 。|
| `statement` | 是 | 官方标准、专家模板或原文要求。保持可追溯，不要过度改写。 |
| `inject_policy` | 是 | 是否进入 prompt 知识包。枚举见下文。 |
| `canonical_label` | 是 | 给大模型注入的短标签。 |
| `label_group` | 后置 | 人工 review 后再程序化合并同义标签。 |
| `prompt_priority` | 后置 | 人工 review 后再排序，控制注入长度。 |

不要一开始就设计太多字段。先完成 `statement -> canonical_label + inject_policy`，后续再补分组和优先级。

## `statement` 的整理规则

`statement` 是原始证据，不是最终 prompt。

整理要求：

- 每条 statement 尽量是一个独立要求。
- 保留官方含义和可追溯来源。
- 删除无用例号，例如“例17”。
- 可删除“简单”等容易弱化考试区分度的词，但不要改变知识边界。
- 每个 statement 末尾保留标点，方便后续多条目拼接。

如果一个官方条目太长，但内部包含多个明确知识要求，可以拆成多条。  
如果一个条目只是态度、意识、价值观、欣赏、社会责任，可以保留，但后续 `inject_policy` 通常不是 `include`。

## `canonical_label` 规则

`canonical_label` 是真正给大模型看的知识标签。它应该短、稳定、可合并。

好标签：

- `三角恒等变换`
- `整数四则混合运算`
- `相似三角形判定与性质`
- `欧姆定律`
- `化学反应速率`
- `Task Response 观点展开`
- `Band 7 让步段模板`

差标签：

- `理解四则运算的意义，能进行整数四则混合运算`
- `经历推导两角差余弦公式的过程`
- `形成初步的模型意识和应用意识`
- `能够在写作中表现出较好的语言能力`

判断标准：

- 如果多条 statement 本质上是同一个知识或方法，应给同一个 `canonical_label`。
- 如果 statement 是学习过程，不是解题可用知识，应提炼成最终可用知识。
- 如果 statement 是素养或意识，不要勉强变成知识点。
- 标签应让 prompt 能写成“你可以使用：X、Y、Z”。

例子：

| statement | canonical_label |
| --- | --- |
| 经历推导两角差余弦公式的过程，知道两角差余弦公式的意义。 | 三角恒等变换 |
| 能从两角差的余弦公式推导出两角和与差的正弦、余弦、正切公式，二倍角公式。 | 三角恒等变换 |
| 会运用数描述生活情境中事物的特征，逐步形成数感、运算能力和初步推理意识。 | 数感与运算能力 |
| 了解液体温度计的工作原理，会用常见温度计测量温度。 | 温度计与温度测量 |
| 认识盐类水解的原理和影响盐类水解的主要因素。 | 盐类水解 |

## `inject_policy` 规则

`inject_policy` 建议只用三个值：

| 值 | 含义 | 是否进入主 prompt |
| --- | --- | --- |
| `include` | 可直接作为解题、评分、反馈、模板选择的知识或方法 | 是 |
| `weak` | 有帮助，但偏思想、背景、应用、实验意识或表达倾向 | 可选，通常低优先级 |
| `exclude` | 不适合直接注入，例如态度价值观、欣赏、纯社会责任、过泛能力 | 否 |

判断口径：

- 能直接指导模型怎么解题、怎么评分、怎么反馈的，标 `include`。
- 对模型有背景约束，但不应占用主 prompt 的，标 `weak`。
- 注入后只会增加噪声的，标 `exclude`。

MathGPT 示例：

| statement 类型 | inject_policy |
| --- | --- |
| “能解一元一次方程” | `include` |
| “了解数学建模思想” | `weak` |
| “认识并欣赏自然界中的轴对称图形” | `exclude` |

RedPen 示例：

| statement 类型 | inject_policy |
| --- | --- |
| “Band 7 Task Response 要求观点清晰、充分展开，并回应题目全部部分” | `include` |
| “鼓励考生形成批判性思维” | `weak` |
| “了解 IELTS 考试的重要性” | `exclude` |

## `label_group` 和 `prompt_priority`

这两个字段不要在第一轮人工标签阶段做。

推荐流程：

1. 大模型逐条生成 `canonical_label` 和 `inject_policy`。
2. 人工 review 标签是否合理。
3. 程序统计重复标签和近似标签。
4. 人工确认合并关系。
5. 程序生成 `label_group` 和 `prompt_priority`。

`label_group` 的作用是把多个标签合成一个 prompt 标签。

示例：

| canonical_label | label_group |
| --- | --- |
| 两角差余弦公式 | 三角恒等变换 |
| 二倍角公式 | 三角恒等变换 |
| 积化和差 | 三角恒等变换 |

如果第一轮已经直接写成 `三角恒等变换`，`label_group` 可以暂时为空。

`prompt_priority` 用来控制最终注入长度。建议后置规则：

- 1：高频核心知识和硬约束。
- 2：常用知识。
- 3：背景、应用、实验、弱相关标签。

## 为什么不用向量检索先做这件事

这类知识注入的第一目标不是“找相似文本”，而是“确定模型允许使用什么”。

因此必须先有结构化表：

- MathGPT：按学段、学科、可用知识方法硬过滤。
- RedPen：按目标分数段、题型、评分维度硬过滤。

向量检索可以后置使用，例如在同一 band 下找相似模板，或在同一学段下找相似知识说明。但它不能替代 `inject_policy` 和 `canonical_label`。

## MathGPT 制作规范

### 输入资料

- 官方课程标准。
- 必要时加入教材目录、考试说明、专家整理知识表。
- 不建议混入无法证明来源的商业知识点，除非明确标记来源和可信度。

### Excel 字段取值

| 字段 | 建议 |
| --- | --- |
| `subject` | `math`、`physics`、`chemistry` |
| `stage_bucket` | 第一学段、第二学段、第三学段、第四学段、高中 |
| `domain` | 数与代数、几何与图形、能量、无机物及其应用等 |
| `theme` | 更具体的课程主题 |
| `canonical_label` | 可直接放进“你可以使用”列表的短知识标签 |
| `inject_policy` | 知识方法为 `include`，素养背景为 `weak/exclude` |

### 注入方式

不要把 statement 原文一股脑注入。

应该先按用户选择的学段生成标签包：

```text
学生当前学段：第四学段。

你可以使用以下数学知识和方法：
- 有理数运算
- 一元一次方程
- 二元一次方程组
- 一次函数
- 全等三角形
- 相似三角形
- 勾股定理
- 统计图表读取

约束：
- 不要把高中方法作为主解法。
- 如果更高学段方法更快，也只能作为补充说明。
```

## RedPen IELTS 作文制作规范

RedPen 的资料不是“知识点白名单”，而是“评分标准 + 分数段模板 + 反馈策略”。

### 推荐字段

可以沿用基础字段，但含义稍作调整：

| 字段 | IELTS 含义 |
| --- | --- |
| `standard_unit_id` | 稳定 ID，例如 `IELTS-WRITING-TASK2-B7-TR-001` |
| `subject` | `ielts_writing` |
| `stage_bucket` | 目标分数段，例如 `Band 6`、`Band 7` |
| `grade_min` | 可填目标 band 下限，例如 6 |
| `grade_max` | 可填目标 band 上限，例如 6.5 |
| `domain` | `Task Response`、`Coherence and Cohesion`、`Lexical Resource`、`Grammar` |
| `theme` | 更具体的模板或评分点，例如 `观点展开`、`让步段`、`复杂句` |
| `statement` | 官方 band descriptor、考官模板说明、反馈规则原文 |
| `inject_policy` | 是否进入该 band 的 prompt |
| `canonical_label` | 短标签，例如 `Band 7 观点充分展开` |
| `label_group` | 后续把同类模板合并 |
| `prompt_priority` | 控制注入顺序 |

### IELTS 标签例子

| 原始材料 | canonical_label | inject_policy |
| --- | --- | --- |
| Band 6 写作能回应题目，但观点展开不充分。 | Band 6 观点展开不足 | `include` |
| Band 7 要求清晰回应题目全部部分，观点充分展开。 | Band 7 充分回应题目并展开观点 | `include` |
| 考官模板：让步段先承认反方合理性，再回到主观点。 | 让步段模板 | `include` |
| 鼓励考生多阅读英文材料。 | 写作输入积累建议 | `weak` |
| IELTS 是国际英语能力测试。 | IELTS 背景介绍 | `exclude` |

### RedPen 注入方式

用户选择目标分数段后，不要检索所有模板。

应先硬过滤：

- 目标 band。
- Task 1 / Task 2。
- 作文类型：opinion、discussion、advantage-disadvantage、problem-solution 等。
- 评分维度：TR、CC、LR、GRA。

再拼 prompt：

```text
用户目标分数：IELTS Writing Band 7。
题型：Task 2 opinion essay。

请按照以下 Band 7 标准和模板给反馈：

[Task Response]
- Band 7 充分回应题目并展开观点
- 主观点必须贯穿全文
- 每个主体段需要 topic sentence + explanation + example

[Coherence and Cohesion]
- 使用清晰段落推进
- 连接词自然，不堆砌

[可用模板]
- 让步段模板
- 原因展开模板
- 例子支撑模板
```

## 人工 review 方法

人工不需要重新读全部原文，只需要看这四列：

```text
statement
inject_policy
canonical_label
备注
```

重点检查：

- `canonical_label` 是否太长。
- 是否把素养类内容误标为 `include`。
- 是否把多个同义知识写成了不同标签。
- 是否有专业错误。
- 是否有越级或跨 band 的标签。

建议 review 后再做两张辅助表：

1. `label_summary`：按 `stage_bucket + canonical_label` 去重。
2. `prompt_pack_preview`：模拟某个年级或 band 最终会注入哪些标签。

## 质量检查清单

交付 Excel 前必须检查：

- 所有行都有 `standard_unit_id`。
- 所有行都有 `statement`。
- 所有行都有 `inject_policy`。
- 所有行都有 `canonical_label`。
- `inject_policy` 只包含 `include`、`weak`、`exclude`。
- `canonical_label` 尽量短，不写长句。
- 同一知识尽量同名。
- 输出 `.xlsx`，不要只给 CSV，避免 Excel 编码问题。
- 保留原始 statement，保证可追溯。

## 最终产物

建议每次资料整理至少输出两个文件：

1. `xxx_canonical_labeled_v0.1.xlsx`
   - 给人工 review。
   - 包含原文、标签、注入策略。

2. `xxx_prompt_pack_preview_v0.1.md`
   - 给产品和研发确认最终 prompt 注入效果。
   - 按学段、分数段或目标用户选择聚合。

Excel 是知识生产表，Markdown 是最终注入预览。两者都要保留版本号。

## 经验结论

这套流程的关键不是把资料切得很细，而是把每条原始要求压成模型能用的短标签。

正确分工是：

- 官方资料负责权威性。
- `statement` 负责可追溯。
- 大模型负责理解和压缩成 `canonical_label`。
- 人工负责 review 标签是否符合产品边界。
- 程序负责去重、分组、排序、生成 prompt 包。

不要让产品经理从零总结专业知识点。产品经理应该 review “这个标签是否合理”，而不是承担教育专家或雅思考官的完整提炼工作。
