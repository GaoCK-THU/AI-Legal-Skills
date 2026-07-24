#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import word_redline as redline


SCRIPT_DIR = Path(__file__).resolve().parent
REDLINE_SCRIPT = SCRIPT_DIR / "word_redline.py"
CLAUSE_PREFIX = re.compile(
    r"^(第[一二三四五六七八九十百千万零〇0-9]+[章节条]|"
    r"[一二三四五六七八九十百千万零〇]+[、.]|[0-9]+[、.])"
)


@dataclass
class PipelineError(Exception):
    error_code: str
    message: str
    extra: dict[str, Any] | None = None


def sha256_file(path: Path) -> str:
    return redline.sha256_file(path)


def load_json(path: str | None) -> dict[str, Any]:
    if path:
        raw = Path(path).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()
    if not raw.strip():
        raise PipelineError("EMPTY_INPUT", "需要通过 --input 或 stdin 提供 JSON。")
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise PipelineError("INVALID_INPUT", "JSON 顶层必须是对象。")
    return loaded


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_snapshot(source: Path) -> dict[str, Any]:
    inspected = redline.inspect_docx(source, start=1, limit=0)
    source_hash = sha256_file(source)
    paragraphs: list[dict[str, Any]] = []
    for paragraph in inspected["paragraphs"]:
        item = dict(paragraph)
        item["block_id"] = redline.block_id(item["index"], item["text"])
        item["text_sha256"] = redline.sha256_text(item["text"])
        paragraphs.append(item)

    clauses: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal current
        material = [item for item in current if not item["is_empty"]]
        if not material:
            current = []
            return
        first = material[0]
        heading = first["text"] if first["is_heading"] else "前言或未编号条款"
        block_ids = [item["block_id"] for item in material]
        clause_key = "|".join(block_ids)
        clauses.append(
            {
                "clause_id": f"clause:{redline.sha256_text(clause_key)[:16]}",
                "heading": heading,
                "text": "\n".join(item["text"] for item in material),
                "block_ids": block_ids,
                "paragraph_indices": [item["index"] for item in material],
                "containers": sorted({item["container"] for item in material}),
                "safe_for_text_redline": all(
                    item["safe_for_text_redline"] for item in material
                ),
            }
        )
        current = []

    for paragraph in paragraphs:
        starts_clause = bool(
            not paragraph["is_empty"]
            and (
                paragraph["is_heading"]
                or CLAUSE_PREFIX.match(paragraph["text"].lstrip())
            )
        )
        if starts_clause and current:
            flush()
        current.append(paragraph)
    flush()

    return {
        "ok": True,
        "schema_version": "pan001-document-snapshot/v2",
        "snapshot_id": f"doc:{source_hash}",
        "source": str(source),
        "source_sha256": source_hash,
        "paragraph_count": len(paragraphs),
        "clause_count": len(clauses),
        "paragraphs": paragraphs,
        "clauses": clauses,
        "structure": inspected["structure"],
        "risk_flags": inspected["risk_flags"],
    }


def require_nonempty_string(value: Any, *, code: str, message: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PipelineError(code, message)
    return value


def compile_intents(payload: dict[str, Any]) -> dict[str, Any]:
    source_value = require_nonempty_string(
        payload.get("source"), code="INVALID_SOURCE", message="source 必须是非空 DOCX 路径。"
    )
    source = Path(source_value)
    snapshot = build_snapshot(source)
    if payload.get("snapshot_id") != snapshot["snapshot_id"]:
        raise PipelineError(
            "SNAPSHOT_CHANGED",
            "intent 使用的 snapshot_id 与当前合同不一致，请重新生成 snapshot。",
            {
                "expected_snapshot_id": payload.get("snapshot_id"),
                "actual_snapshot_id": snapshot["snapshot_id"],
            },
        )
    if payload.get("source_sha256") != snapshot["source_sha256"]:
        raise PipelineError(
            "SOURCE_CHANGED",
            "合同快照与当前文件不一致，请重新生成 snapshot。",
            {
                "expected_source_sha256": payload.get("source_sha256"),
                "actual_source_sha256": snapshot["source_sha256"],
            },
        )

    intents = payload.get("intents")
    if not isinstance(intents, list) or not intents:
        raise PipelineError("EMPTY_INTENTS", "intents 必须是非空数组。")

    blocks = {item["block_id"]: item for item in snapshot["paragraphs"]}
    used_blocks: set[str] = set()
    operations: list[dict[str, Any]] = []
    expectations: list[dict[str, Any]] = []
    intent_records: list[dict[str, Any]] = []

    for index, intent in enumerate(intents, start=1):
        if not isinstance(intent, dict):
            raise PipelineError("INVALID_INTENT", f"第 {index} 个 intent 必须是对象。")
        intent_id = str(intent.get("intent_id") or f"intent-{index}")
        anchor = intent.get("anchor")
        if not isinstance(anchor, dict):
            raise PipelineError("MISSING_ANCHOR", f"第 {index} 个 intent 缺少 anchor。")
        anchor_block_id = anchor.get("block_id")
        if anchor_block_id not in blocks:
            raise PipelineError(
                "UNKNOWN_BLOCK",
                f"第 {index} 个 intent 的 block_id 不在当前快照中。",
                {"block_id": anchor_block_id, "intent_id": intent_id},
            )
        if anchor_block_id in used_blocks:
            raise PipelineError(
                "DUPLICATE_BLOCK_INTENT",
                "同一快照 block 只允许一个 intent；请在法律意图层合并。",
                {"block_id": anchor_block_id, "intent_id": intent_id},
            )
        used_blocks.add(anchor_block_id)
        block = blocks[anchor_block_id]
        source_quote = require_nonempty_string(
            anchor.get("source_quote"),
            code="MISSING_SOURCE_QUOTE",
            message=f"第 {index} 个 intent 缺少连续原文 source_quote。",
        )
        if source_quote not in block["text"]:
            raise PipelineError(
                "SOURCE_QUOTE_MISMATCH",
                f"第 {index} 个 intent 的 source_quote 不在锚定 block 中。",
                {"block_id": anchor_block_id, "intent_id": intent_id},
            )

        risk = require_nonempty_string(
            intent.get("risk"), code="MISSING_RISK", message=f"第 {index} 个 intent 缺少 risk。"
        )
        desired_effect = require_nonempty_string(
            intent.get("desired_effect"),
            code="MISSING_DESIRED_EFFECT",
            message=f"第 {index} 个 intent 缺少 desired_effect。",
        )
        dependency_group = str(intent.get("dependency_group") or intent_id)
        treatment = intent.get("treatment")
        common = {
            "locator": {"paragraph_index": block["index"], "block_id": block["block_id"]},
            "original_text": block["text"],
            "original_text_sha256": block["text_sha256"],
            "intent_id": intent_id,
            "dependency_group": dependency_group,
        }

        if treatment == "edit":
            if not block["safe_for_text_redline"]:
                raise PipelineError(
                    "UNSAFE_BLOCK",
                    "目标 block 包含复杂对象或已有修订，不能自动渲染正文。",
                    {"block_id": anchor_block_id, "intent_id": intent_id},
                )
            proposed_text = require_nonempty_string(
                intent.get("proposed_text"),
                code="MISSING_PROPOSED_TEXT",
                message=f"第 {index} 个 edit intent 缺少 proposed_text。",
            )
            if proposed_text == block["text"]:
                raise PipelineError(
                    "NO_CHANGE", "拟议文本与原 block 相同。", {"intent_id": intent_id}
                )
            operations.append({"type": "render_block", **common, "new_text": proposed_text})
            expectations.append(
                {
                    "paragraph_index": block["index"],
                    "block_id": block["block_id"],
                    "intent_id": intent_id,
                    "dependency_group": dependency_group,
                    "original_text": block["text"],
                    "expected_text": proposed_text,
                }
            )
        elif treatment == "comment":
            comment_text = require_nonempty_string(
                intent.get("comment_text"),
                code="MISSING_COMMENT_TEXT",
                message=f"第 {index} 个 comment intent 缺少 comment_text。",
            )
            operations.append(
                {
                    "type": "add_comment",
                    **common,
                    "target_text": source_quote,
                    "comment_text": comment_text,
                }
            )
        else:
            raise PipelineError(
                "INVALID_TREATMENT", f"第 {index} 个 intent 的 treatment 仅支持 edit 或 comment。"
            )

        intent_records.append(
            {
                "intent_id": intent_id,
                "block_id": anchor_block_id,
                "source_quote": source_quote,
                "risk": risk,
                "desired_effect": desired_effect,
                "treatment": treatment,
                "dependency_group": dependency_group,
            }
        )

    return {
        "source": str(source),
        "source_sha256": snapshot["source_sha256"],
        "snapshot_id": snapshot["snapshot_id"],
        "author": str(payload.get("author") or redline.DEFAULT_AUTHOR),
        "operations": operations,
        "expectations": expectations,
        "intent_records": intent_records,
        "compiler": "pan001-anchored-block-renderer/v2",
    }


def parse_engine_payload(stdout: str) -> dict[str, Any]:
    try:
        loaded = json.loads(stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": stdout.strip() or "执行引擎未返回 JSON。"}
    return loaded if isinstance(loaded, dict) else {"ok": False, "error": "执行引擎返回类型错误。"}


def preflight_plan(plan: dict[str, Any]) -> dict[str, Any]:
    source_value = require_nonempty_string(
        plan.get("source"), code="INVALID_SOURCE", message="计划中的 source 必须是非空路径。"
    )
    source = Path(source_value)
    redline.ensure_docx(source)
    original_hash = sha256_file(source)
    if plan.get("source_sha256") != original_hash:
        raise PipelineError(
            "SOURCE_CHANGED",
            "计划中的 source_sha256 与当前文件不一致。",
            {
                "expected_source_sha256": plan.get("source_sha256"),
                "actual_source_sha256": original_hash,
            },
        )

    with tempfile.TemporaryDirectory(prefix="pan001-preflight-") as temp_dir:
        staged = Path(temp_dir) / source.name
        shutil.copy2(source, staged)
        simulated_plan = dict(plan)
        simulated_plan["source"] = str(staged)
        simulated_plan["source_sha256"] = sha256_file(staged)
        simulated_plan.pop("output", None)
        simulated_plan["in_place"] = True
        result = subprocess.run(
            [sys.executable, str(REDLINE_SCRIPT), "apply"],
            input=json.dumps(simulated_plan, ensure_ascii=False),
            capture_output=True,
            text=True,
            check=False,
        )
        engine_payload = parse_engine_payload(result.stdout)
        if result.returncode != 0 or not engine_payload.get("ok"):
            raise PipelineError(
                str(engine_payload.get("error_code") or "PREFLIGHT_APPLY_FAILED"),
                "模拟执行未通过，未修改原合同。",
                {"engine": engine_payload, "stderr": result.stderr.strip()},
            )

        inspected = redline.inspect_docx(staged, start=1, limit=0)
        actual_by_index = {item["index"]: item for item in inspected["paragraphs"]}
        mismatches = []
        for item in plan.get("expectations", []):
            actual = actual_by_index.get(item["paragraph_index"], {})
            accepted_text = actual.get("text")
            rejected_text = actual.get("rejected_text")
            if (
                accepted_text != item["expected_text"]
                or rejected_text != item["original_text"]
            ):
                mismatches.append(
                    {
                        "paragraph_index": item["paragraph_index"],
                        "block_id": item["block_id"],
                        "intent_id": item["intent_id"],
                        "expected_accepted_text": item["expected_text"],
                        "actual_accepted_text": accepted_text,
                        "expected_rejected_text": item["original_text"],
                        "actual_rejected_text": rejected_text,
                    }
                )
        if mismatches:
            raise PipelineError(
                "REVISION_VIEW_MISMATCH",
                "模拟执行的接受或拒绝修订视图与预期不一致。",
                {"mismatches": mismatches},
            )

    if sha256_file(source) != original_hash:
        raise PipelineError("SOURCE_MODIFIED_DURING_PREFLIGHT", "预检期间原合同发生变化。")
    return {
        "ok": True,
        "stage": "preflight",
        "source": str(source),
        "source_sha256": original_hash,
        "operation_count": len(plan.get("operations", [])),
        "expectation_count": len(plan.get("expectations", [])),
        "engine_verify": engine_payload.get("verify", {}),
        "original_preserved": True,
    }


def group_plan(plan: dict[str, Any], group_name: str, operations: list[dict[str, Any]]) -> dict[str, Any]:
    intent_ids = {str(operation.get("intent_id")) for operation in operations}
    return {
        **plan,
        "operations": operations,
        "expectations": [
            item for item in plan.get("expectations", []) if item.get("intent_id") in intent_ids
        ],
        "intent_records": [
            item for item in plan.get("intent_records", []) if item.get("intent_id") in intent_ids
        ],
        "preflight_group": group_name,
    }


def preflight_groups(plan: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for operation in plan["operations"]:
        groups.setdefault(str(operation["dependency_group"]), []).append(operation)

    accepted_operations: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for group_name, operations in groups.items():
        candidate = group_plan(plan, group_name, operations)
        try:
            preflight = preflight_plan(candidate)
        except PipelineError as exc:
            result: dict[str, Any] = {
                "dependency_group": group_name,
                "status": "rejected",
                "operation_count": len(operations),
                "intent_ids": [str(operation["intent_id"]) for operation in operations],
                "error_code": exc.error_code,
                "error": exc.message,
            }
            if exc.extra:
                result["detail"] = exc.extra
            results.append(result)
            continue
        accepted_operations.extend(operations)
        results.append(
            {
                "dependency_group": group_name,
                "status": "accepted",
                "operation_count": len(operations),
                "intent_ids": [str(operation["intent_id"]) for operation in operations],
                "preflight": preflight,
            }
        )

    if not accepted_operations:
        raise PipelineError(
            "NO_ACCEPTED_GROUPS",
            "所有 dependency_group 均未通过预检，未生成可应用计划。",
            {"group_results": results},
        )

    accepted_groups = {
        item["dependency_group"] for item in results if item["status"] == "accepted"
    }
    prepared = {
        **plan,
        "operations": accepted_operations,
        "expectations": [
            item for item in plan.get("expectations", []) if item["dependency_group"] in accepted_groups
        ],
        "intent_records": [
            item for item in plan.get("intent_records", []) if item["dependency_group"] in accepted_groups
        ],
        "group_results": results,
    }
    preflight_plan(prepared)
    return prepared, results


def validate_evidence_dir(source: Path, evidence_dir_value: str | None) -> Path | None:
    if not evidence_dir_value:
        return None
    evidence_dir = Path(evidence_dir_value).resolve()
    source_parent = source.parent.resolve()
    if evidence_dir == source_parent or source_parent in evidence_dir.parents:
        raise PipelineError(
            "INVALID_EVIDENCE_DIR",
            "evidence-dir 不得位于合同目录内；请使用受控的任务证据目录。",
        )
    return evidence_dir


def validate_plan_path(source: Path, plan_path_value: str | None) -> Path | None:
    if not plan_path_value:
        return None
    plan_path = Path(plan_path_value).resolve()
    source_parent = source.parent.resolve()
    if plan_path.parent == source_parent or source_parent in plan_path.parents:
        raise PipelineError(
            "INVALID_PLAN_PATH",
            "output-plan 不得位于合同目录内；请使用系统临时目录或受控任务目录。",
        )
    return plan_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="pan001 稳定锚点合同管道")
    sub = parser.add_subparsers(dest="command", required=True)
    snapshot = sub.add_parser("snapshot", help="从 DOCX 生成稳定 block 和条款对象")
    snapshot.add_argument("--source", required=True)
    prepare = sub.add_parser("prepare", help="编译高层意图并按 dependency_group 预检")
    prepare.add_argument("--input", help="意图 JSON；不传则从 stdin 读取")
    prepare.add_argument("--output-plan", help="把可应用计划写到该路径")
    prepare.add_argument("--evidence-dir", help="受控证据目录；不得位于合同目录内")
    preflight = sub.add_parser("preflight", help="对已编译计划做模拟执行")
    preflight.add_argument("--input", help="计划 JSON；不传则从 stdin 读取")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    evidence_dir: Path | None = None
    try:
        if args.command == "snapshot":
            payload = build_snapshot(Path(args.source))
        elif args.command == "prepare":
            intents = load_json(args.input)
            source = Path(str(intents.get("source") or ""))
            evidence_dir = validate_evidence_dir(source, args.evidence_dir)
            output_plan = validate_plan_path(source, args.output_plan)
            if evidence_dir:
                write_json(evidence_dir / "01-intents.json", intents)
            compiled = compile_intents(intents)
            if evidence_dir:
                write_json(evidence_dir / "02-compiled-plan.json", compiled)
            prepared, group_results = preflight_groups(compiled)
            if output_plan:
                write_json(output_plan, prepared)
            if evidence_dir:
                write_json(evidence_dir / "03-group-results.json", {"groups": group_results})
                write_json(evidence_dir / "04-prepared-plan.json", prepared)
            rejected = [item for item in group_results if item["status"] == "rejected"]
            payload = {
                "ok": True,
                "stage": "prepared_partial" if rejected else "prepared",
                "compiler": prepared["compiler"],
                "operation_count": len(prepared["operations"]),
                "accepted_group_count": len(group_results) - len(rejected),
                "rejected_group_count": len(rejected),
                "group_results": group_results,
                "compiled_plan_path": str(output_plan) if output_plan else None,
                "evidence_dir": str(evidence_dir) if evidence_dir else None,
                "original_preserved": True,
            }
        elif args.command == "preflight":
            payload = preflight_plan(load_json(args.input))
        else:
            parser.error(f"未知命令: {args.command}")
            return
    except PipelineError as exc:
        payload = {"ok": False, "error_code": exc.error_code, "error": exc.message}
        if exc.extra:
            payload.update(exc.extra)
        if evidence_dir:
            write_json(evidence_dir / "error.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    except json.JSONDecodeError as exc:
        payload = {"ok": False, "error_code": "INVALID_JSON", "error": str(exc)}
        if evidence_dir:
            write_json(evidence_dir / "error.json", payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
