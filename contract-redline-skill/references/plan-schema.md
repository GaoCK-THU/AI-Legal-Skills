# 稳定锚点渲染计划 schema v2

候选版主流程必须由 `contract_pipeline.py prepare` 生成计划；LLM不得手写或修改本文件的底层结构。

## 顶层结构

```json
{
  "source": "/path/to/contract.docx",
  "source_sha256": "当前快照哈希",
  "snapshot_id": "doc:...",
  "author": "审阅人",
  "operations": [],
  "group_results": []
}
```

## 正文渲染 `render_block`

一个正文 intent 只产生一个 `render_block`：

```json
{
  "type": "render_block",
  "locator": {"paragraph_index": 72, "block_id": "body:p0072-..."},
  "original_text": "当前快照中的完整block原文",
  "original_text_sha256": "完整原文SHA-256",
  "new_text": "完整拟议终稿",
  "intent_id": "DELIVERY-01",
  "dependency_group": "DELIVERY-REMEDIES"
}
```

执行引擎只接受同时匹配 `paragraph_index + block_id + original_text + original_text_sha256` 的当前段落。任何一项不一致都返回 `BLOCK_ANCHOR_MISMATCH`，不得在全文中模糊搜索替代位置。

渲染器对该 block 只执行一次 diff，并一次性生成 tracked changes。不得把完整终稿拆成若干需要在变化后段落中再次搜索的字符串operation。

## 稳定锚点批注 `add_comment`

批注同样携带 `paragraph_index`、`block_id`、完整原文及其哈希；`target_text` 必须是block中连续存在的原文。

## 依赖组

- `prepare`按 `dependency_group` 独立预检。
- 同一组全部成功才进入可应用计划。
- 无关组可以在某组失败时继续交付。
- 所有成功组还必须通过一次组合预检。
- 全部组失败时不生成可应用计划。

## 事务与证据

- `word_redline.py apply` 在临时工作副本完成全部已接受operations，技术校验通过后原子写回。
- 源哈希变化、block锚点变化、部分写入或结构校验失败均取消整次写回。
- 使用 `--evidence-dir` 时，管道保存原始intents、完整编译计划、分组结果、可应用计划或错误。
- evidence目录不得位于合同目录内；合同目录不得遗留计划、临时DOCX或备份。

## 兼容性边界

`word_redline.py` 为旧调用保留旧operation，但candidate-002主流程只生成 `render_block` 和稳定锚点 `add_comment`。
