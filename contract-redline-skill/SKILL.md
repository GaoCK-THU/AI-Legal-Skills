---
name: 合同修订
description: 合同修订红线：把合同审查判断直接写入 `.docx` 原生 tracked changes。用户要求修订合同、按甲方/乙方/委托人/受托人/采购人/供应商立场改合同、输出 Word 红线稿、保留修订痕迹、不要审查意见而要直接改 `.docx` 时使用。
---

# 合同修订

目标：交付可由 Word/WPS 识别的 DOCX 原生修订稿，而不是输出长篇审查意见。

核心原则是**闭环红线**：每一处正文修改都必须同时满足必要、稳定锚定、到位。

- 必要：不改会实质影响委托方核心权利、履行可操作性或风险救济。
- 稳定锚定：每个法律意图绑定最新快照中的唯一block，并由程序一次性渲染；关联修改按依赖组共同成败。
- 到位：改后在当前句或当前款内补齐主体、条件、期限、标准、例外或责任后果，不留下半截风险。

## 1. 输入门槛

开始前确认：

1. 合同文件路径，必须是 `.docx`
2. 代表哪一方，例如甲方、乙方、委托人、受托人、采购人、供应商
3. 市场地位：强势、平等、弱势
4. 修订重点或特别关注条款
5. 修订人姓名，默认 `审阅人`

缺少第 2、3、4 项时，先追问。只有用户明确说“测试”“自行判断”或上下文已经足够时，才可用合理假设继续，并在最终结果中说明假设。

默认交付方式是**事务式原地修订**：先在自动清理的临时工作副本中完成全部操作和校验，全部通过后一次性替换原文件。任务结束后只保留原文件路径，不留下修订稿副本或计划文件。只有用户明确要求另存修订稿时，才设置 `output`。

完成标准：已经拿到可编辑 `.docx` 和明确修订立场；输出方式没有额外文件歧义。否则停止在追问或失败分流。

## 2. 边界分流

遇到以下情况，先读 `references/failure-handling.md`，再决定停止、追问或降级为批注：

- 输入不是原生 `.docx`
- 文档损坏、无法解析或疑似由 `.doc`/PDF/OCR 转换而来
- 已有修订导致定位不稳定
- 涉及表格嵌套、页眉页脚、文本框、域、自动目录等复杂对象
- 用户要求整份重写、跨段重构或整体排版重做

已有他人修订时，默认只追加新修订，不接受或拒绝既有修订；用户明确要求接受/拒绝时才处理。

完成标准：确认本次能安全自动修订；若不能，已说明原因和可行替代。

## 3. 判断审查档位

形成修订动作前，先读：

- `references/review-framework.md`
- `references/review-rules.md`

先判断轻量审查还是标准审查：

- 轻量审查：小额、常规、低风险、履行关系清楚，只处理核心风险。
- 标准审查：金额、周期、责任后果或高敏事项较重，或多个核心条款相互牵连。

不要仅因委托方市场地位强势就高密度、强对抗式修订。金额、比例、费率、违约金、履行期限、通知期限、付款周期等交易参数，只有在能结合交易规模、风险敞口、履行难度和可接受性说明必要时，才直接改正文；否则用批注提示商业确认。

完成标准：已确定审查档位，并能用一句话说明为什么。

## 4. 读取解析器快照与稳定锚点

使用前置管道生成包含 `snapshot_id`、解析器所有的稳定 `block_id`、结构性 `clause_id` 和源文件哈希的合同快照：

```bash
python3 scripts/contract_pipeline.py snapshot --source '/path/to/contract.docx'
```

快照由程序从最新原生 DOCX 生成；不要自行重建、估算或沿用旧轮次的 block 编号、条款编号或文件哈希。`block_id` 仅在当前 `snapshot_id` 下有效。阅读快照直到覆盖标题、核心义务、付款/验收、违约、解除、争议解决和签署页附近内容。

检查时记录：

- block 编号和标题位置
- 拟处理段落的 `block_id`、连续原文 `source_quote` 和所属 `clause_id`
- `risk_flags`、已有修订与批注数量、表格/嵌套表格、页眉页脚、文本框、域、超链接、绘图和内容控件
- 目标段落的 `container`、`safe_for_text_redline` 及局部复杂对象标记
- 空白日期、空白金额、`【  】`、下划线等占位内容

完成标准：每个拟处理点都直接复制了当前快照中的 `block_id`，`source_quote` 是该 block 中真实连续出现的原文，并已确认对应条款、容器及 `safe_for_text_redline`。

## 5. 生成闭环修订意图

不要直接手写底层 operation。按照 `references/intent-schema.md` 生成高层 intent，至少写明：

1. `anchor.block_id` 和连续原文 `anchor.source_quote`
2. 风险 `risk`
3. 期望法律效果 `desired_effect`
4. 处理方式 `edit` 或 `comment`
5. `edit` 的完整拟议 block `proposed_text`，或 `comment` 的批注文字
6. 法律上必须共同成立的修改使用同一 `dependency_group`

每个 intent 先过三道闸：

- 必要性闸：这处不改是否会造成明确风险、歧义、履行障碍或谈判劣势？
- 闭环闸：改后是否补齐条件、例外、责任边界或救济路径？
- 可渲染闸：是否对应一个安全 block，且拟议结果可以由程序一次性渲染为修订？

生成规则：

- LLM 输出修改完成后的完整 block，不负责选择 `replace_text`、`insert`、`delete`、段落号、occurrence 或字符位置。
- 程序验证 `snapshot_id + block_id + source_quote + block全文哈希`，再把该 block 一次性渲染成 tracked changes；不得在已变化的段落上连续搜索旧字符串。
- 不修改空白填写项和未确认的商业参数。
- 无法稳定落地但需要提示的问题，从一开始就选择 `comment`；不得在技术预检失败后削弱或改写法律意图来迁就渲染器。
- 跨 block 联动修改使用同一 `dependency_group`；复杂对象或无可靠锚点时转为批注或人工处理。

完成标准：每个 intent 都有明确法律目的、最新稳定锚点和完整拟议结果；没有底层 operation，也没有为风格优化加入的修订。

## 6. 按依赖组编译与预检

把 intent JSON 放在系统临时目录，通过程序生成底层计划并在临时 DOCX 上完整模拟执行：

```bash
python3 scripts/contract_pipeline.py prepare \
  --input '/tmp/contract-intents.json' \
  --output-plan '/tmp/contract-prepared-plan.json'
```

在评测、调试或用户授权保留诊断材料时，额外指定受控证据目录；该目录不得位于合同目录内：

```bash
python3 scripts/contract_pipeline.py prepare \
  --input '/tmp/contract-intents.json' \
  --output-plan '/tmp/contract-prepared-plan.json' \
  --evidence-dir '/path/to/task/evidence'
```

`prepare` 必须验证：当前快照、连续原文、block全文哈希、intent schema、block安全性、一次性渲染、DOCX技术校验，以及模拟后的可见文本与 `proposed_text` 一致性。

程序按 `dependency_group` 独立预检：

- 同一组全部成功才进入可应用计划。
- 某组失败时整组隔离，不影响无关组。
- 组合后的全部成功组再做一次总预检。
- 如果所有组失败，则安全停止。
- 技术错误由程序报告和修复；不得让 LLM 为定位、offset、XML 或格式错误重写法律结果。

受控证据目录保存输入 intent、完整编译计划、分组结果、可应用计划或错误；合同目录仍不得遗留计划、临时DOCX或备份。

完成标准：`stage=prepared` 或 `prepared_partial`，原合同哈希不变，并取得只包含成功 dependency groups 的程序计划和明确的失败组清单。

## 7. 应用修订

优先从 stdin 传入 JSON，不要在合同目录生成 `ops.json`。确需临时计划文件时，只放系统临时目录，并在执行后立即删除。

```bash
python3 scripts/word_redline.py apply < '/tmp/contract-prepared-plan.json'
```

底层计划由程序生成，不得由 LLM 重写。正文只使用稳定锚定的 `render_block`，每个 block 一次性渲染；批注也必须携带同一稳定 block 锚点。计划包含 `source_sha256`；源文件在预检后发生变化时，`apply` 必须拒绝旧计划。默认在临时工作副本中执行；全部已接受组和技术校验成功后原子替换原文件。

脚本要求见 `references/plan-schema.md`。修订作者默认 `审阅人`。修订和批注时间统一使用北京时间 `+08:00`，最后一处时间不晚于实际执行时间；各block渲染或批注根据文字长度和所在段落上下文长度形成基础间隔，并叠加小幅自然波动。同一block渲染产生的删除与插入使用同一时间。

完成标准：脚本成功返回，原文件路径已原子更新，没有遗留临时 DOCX 或计划文件，并显示已应用 block、批注和被隔离依赖组摘要。

## 8. 校验交付

应用后必须校验：

```bash
python3 scripts/word_redline.py verify --source '/path/to/contract.docx'
```

校验至少确认：

- `has_revisions` 为 true
- 新增插入、删除和批注数量与 operation 计划精确一致
- 作者为 `审阅人` 或用户指定作者
- 时间戳含 `+08:00`，不存在新增未来时间
- ZIP/XML 完整，修订 ID 唯一，批注锚点和关系完整

脚本校验通过后，再 inspect 受影响段落并人工复读可见文本，确认没有句义悬空、标点残缺、重复文本或修改错位。结构校验不能替代这一步语义复核。

如果校验失败、定位失败、只写入部分修订，或发现半成品修改，停止并说明，不交付为完成稿。

完成标准：原文件已成为可交付的修订稿，并附简短摘要。

## 输出格式

最终只回复：

- 已更新的原文件路径；用户明确要求另存时才回复另存路径
- 校验结果：修订数、批注数、作者、时间戳是否正常
- 审查档位及一句话理由
- 实际修订摘要
- 被隔离的 dependency groups、未自动处理或需用户确认的问题

不要输出长篇审查意见、单独的“修订建议.md”或内部推理过程。

## 参考资料

- `references/review-framework.md`：业务判断、条款扫描、动作选择
- `references/review-rules.md`：轻量/标准审查档位与小额常规合同少改规则
- `references/plan-schema.md`：`word_redline.py apply` 输入格式
- `references/intent-schema.md`：LLM 高层修订意图格式
- `references/failure-handling.md`：失败分流与边界处理

## 修改记录

详见 [CHANGELOG.md](./CHANGELOG.md)
