# 高层修订意图 schema v2

LLM只表达法律判断和拟议结果。所有定位信息必须直接复制当前 `snapshot`；程序负责稳定锚点校验和Word tracked-changes渲染。

```json
{
  "source": "/path/to/contract.docx",
  "source_sha256": "snapshot 返回值",
  "snapshot_id": "snapshot 返回值",
  "author": "审阅人",
  "intents": [
    {
      "intent_id": "PAYMENT-01",
      "anchor": {
        "block_id": "snapshot 返回的 block_id",
        "source_quote": "该 block 中真实连续出现的原文"
      },
      "risk": "付款条件完全取决于甲方单方核验",
      "desired_effect": "明确核验义务并避免无限期拖延付款",
      "treatment": "edit",
      "proposed_text": "该 block 接受全部拟议修订后的完整文本",
      "dependency_group": "PAYMENT-ACCEPTANCE"
    },
    {
      "intent_id": "PARAMETER-01",
      "anchor": {
        "block_id": "snapshot 返回的 block_id",
        "source_quote": "付款期限"
      },
      "risk": "付款期限属于待确认商业参数",
      "desired_effect": "提示用户确认而不擅自填写期限",
      "treatment": "comment",
      "comment_text": "请确认付款期限。",
      "dependency_group": "PARAMETER-01"
    }
  ]
}
```

## 不变量

- `snapshot_id`、`source_sha256`、`block_id` 必须来自同一次最新 snapshot。
- `source_quote` 必须非空，并在锚定 block 中真实、连续出现；不得概括、拼接或改写。
- 每个 block 只允许一个 intent；同一 block 的多个法律问题应合并为一个完整结果。
- `edit` 必须给出完整 `proposed_text`；程序一次性渲染该 block，不生成字符串搜索 operation。
- `comment` 的 `source_quote` 同时作为批注目标。
- 法律上必须共同成立的跨 block 修改使用同一 `dependency_group`；未填写时默认为 `intent_id`。
- 跨 block 重构、复杂对象、已有修订内部文字和无可靠锚点的内容，不自动修改正文。
- 技术预检失败不得触发法律文本改写；应隔离该依赖组、降级为预先设计的批注方案或人工处理。
