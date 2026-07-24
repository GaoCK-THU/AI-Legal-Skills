#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile


W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
DEFAULT_AUTHOR = "审阅人"
LOCAL_TZ = ZoneInfo("Asia/Shanghai")
PLACEHOLDER_PATTERNS = (
    re.compile(r"【\s*】"),
    re.compile(r"_{3,}"),
    re.compile(r"（\s*年\s*月\s*日\s*）"),
)
CORE_NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
}
PKG_REL_NS = {"pr": "http://schemas.openxmlformats.org/package/2006/relationships"}
CONTENT_TYPES_NS = {"ct": "http://schemas.openxmlformats.org/package/2006/content-types"}
KNOWN_NAMESPACES = {
    "wpc": "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "o": "urn:schemas-microsoft-com:office:office",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "v": "urn:schemas-microsoft-com:vml",
    "wp14": "http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "w10": "urn:schemas-microsoft-com:office:word",
    "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
    "wpg": "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup",
    "wpi": "http://schemas.microsoft.com/office/word/2010/wordprocessingInk",
    "wne": "http://schemas.microsoft.com/office/word/2006/wordml",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "wpsCustomData": "http://www.wps.cn/officeDocument/2013/wpsCustomData",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "dcmitype": "http://purl.org/dc/dcmitype/",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
}

for prefix, uri in KNOWN_NAMESPACES.items():
    ET.register_namespace(prefix, uri)


def w_tag(name: str) -> str:
    return f"{{{W_NS['w']}}}{name}"


def serialize_word_document(root: ET.Element) -> bytes:
    ignorable_key = f"{{{KNOWN_NAMESPACES['mc']}}}Ignorable"
    ignorable = root.attrib.get(ignorable_key, "")
    if ignorable:
        start_tag = ET.tostring(root, encoding="unicode", xml_declaration=False).split(">", 1)[0]
        for prefix in ignorable.split():
            uri = KNOWN_NAMESPACES.get(prefix)
            if uri and f"xmlns:{prefix}=" not in start_tag:
                root.set(f"xmlns:{prefix}", uri)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def fail(message: str, *, code: int = 1, extra: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"ok": False, "error": message}
    if extra:
        payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(code)


def ensure_docx(path: Path) -> None:
    if not path.exists():
        fail(f"文件不存在: {path}")
    if not path.is_file():
        fail(f"路径不是文件: {path}")
    if path.suffix.lower() != ".docx":
        fail(f"仅支持 .docx 文件: {path}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def block_id(paragraph_index: int, text: str) -> str:
    """Return a snapshot-scoped block anchor owned by the parser."""
    return f"body:p{paragraph_index:04d}-{sha256_text(text)[:16]}"


def parse_styles(docx_path: Path) -> tuple[dict[str, str], dict[str, str]]:
    style_names: dict[str, str] = {}
    style_types: dict[str, str] = {}
    with ZipFile(docx_path) as zf:
        try:
            xml = zf.read("word/styles.xml")
        except KeyError:
            return style_names, style_types
    root = ET.fromstring(xml)
    for style in root.findall("w:style", W_NS):
        style_id = style.attrib.get(f"{{{W_NS['w']}}}styleId")
        style_type = style.attrib.get(f"{{{W_NS['w']}}}type", "")
        name_el = style.find("w:name", W_NS)
        style_name = name_el.attrib.get(f"{{{W_NS['w']}}}val", "") if name_el is not None else ""
        if style_id:
            style_names[style_id] = style_name
            style_types[style_id] = style_type
    return style_names, style_types


def paragraph_text(paragraph: ET.Element) -> str:
    return visible_element_text(paragraph).replace("\r", "")


def document_paragraphs(body: ET.Element) -> list[ET.Element]:
    return list(body.iterfind(".//w:p", W_NS))


def is_heading(text: str, style_name: str, style_id: str) -> bool:
    style_blob = f"{style_name} {style_id}".lower()
    if any(token in style_blob for token in ["heading", "title", "标题", "章标题", "条标题"]):
        return True
    return bool(
        re.match(
            r"^(第[一二三四五六七八九十百千万零〇0-9]+[章节条]|[一二三四五六七八九十]+、)",
            text.lstrip(),
        )
    )


def build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def has_ancestor(
    element: ET.Element,
    ancestor_tag: str,
    parent_map: dict[ET.Element, ET.Element],
) -> bool:
    current = parent_map.get(element)
    while current is not None:
        if current.tag == ancestor_tag:
            return True
        current = parent_map.get(current)
    return False


def paragraph_structure_flags(
    paragraph: ET.Element,
    parent_map: dict[ET.Element, ET.Element],
) -> dict[str, Any]:
    in_textbox = has_ancestor(paragraph, w_tag("txbxContent"), parent_map)
    in_table = has_ancestor(paragraph, w_tag("tbl"), parent_map)
    has_fields = bool(
        paragraph.findall(".//w:fldChar", W_NS)
        or paragraph.findall(".//w:instrText", W_NS)
        or paragraph.findall(".//w:fldSimple", W_NS)
    )
    has_drawing = bool(
        paragraph.findall(".//w:drawing", W_NS)
        or paragraph.findall(".//w:pict", W_NS)
        or paragraph.findall(".//w:object", W_NS)
    )
    has_revisions = bool(
        paragraph.findall(".//w:ins", W_NS)
        or paragraph.findall(".//w:del", W_NS)
        or paragraph.findall(".//w:moveFrom", W_NS)
        or paragraph.findall(".//w:moveTo", W_NS)
    )
    has_comments = bool(
        paragraph.findall(".//w:commentRangeStart", W_NS)
        or paragraph.findall(".//w:commentRangeEnd", W_NS)
        or paragraph.findall(".//w:commentReference", W_NS)
    )
    has_hyperlinks = bool(paragraph.findall(".//w:hyperlink", W_NS))
    has_content_controls = bool(paragraph.findall(".//w:sdt", W_NS))
    text = paragraph_text(paragraph)
    placeholders = [
        match.group(0)
        for pattern in PLACEHOLDER_PATTERNS
        for match in pattern.finditer(text)
    ]
    return {
        "container": "textbox" if in_textbox else "table" if in_table else "body",
        "has_revisions": has_revisions,
        "has_comments": has_comments,
        "has_fields": has_fields,
        "has_hyperlinks": has_hyperlinks,
        "has_drawing": has_drawing,
        "has_content_controls": has_content_controls,
        "has_placeholder": bool(placeholders),
        "placeholders": placeholders,
        "safe_for_text_redline": not (
            in_textbox
            or has_fields
            or has_hyperlinks
            or has_drawing
            or has_content_controls
            or has_revisions
        ),
    }


def inspect_docx(docx_path: Path, *, start: int, limit: int) -> dict[str, Any]:
    ensure_docx(docx_path)
    style_names, _style_types = parse_styles(docx_path)
    with ZipFile(docx_path) as zf:
        try:
            xml = zf.read("word/document.xml")
        except KeyError:
            fail("文档缺少 word/document.xml，无法解析。")
        names = zf.namelist()
        comments_xml = zf.read("word/comments.xml") if "word/comments.xml" in names else b""
        header_parts = [name for name in names if re.fullmatch(r"word/header\d+\.xml", name)]
        footer_parts = [name for name in names if re.fullmatch(r"word/footer\d+\.xml", name)]
    root = ET.fromstring(xml)
    body = root.find("w:body", W_NS)
    if body is None:
        fail("文档 body 为空，无法解析。")

    parent_map = build_parent_map(root)
    paragraphs: list[dict[str, Any]] = []
    for idx, paragraph in enumerate(document_paragraphs(body), start=1):
        text = paragraph_text(paragraph)
        p_style = paragraph.find("w:pPr/w:pStyle", W_NS)
        style_id = p_style.attrib.get(f"{{{W_NS['w']}}}val", "") if p_style is not None else ""
        style_name = style_names.get(style_id, "")
        structure_flags = paragraph_structure_flags(paragraph, parent_map)
        paragraphs.append(
            {
                "index": idx,
                "text": text,
                "rejected_text": paragraph_rejected_text(paragraph),
                "style_id": style_id,
                "style_name": style_name,
                "is_heading": is_heading(text, style_name, style_id),
                "is_empty": text.strip() == "",
                **structure_flags,
            }
        )

    start_index = max(start, 1)
    end_index = min(len(paragraphs), start_index + max(limit, 0) - 1) if limit > 0 else len(paragraphs)
    window = paragraphs[start_index - 1 : end_index]
    headings = [p for p in paragraphs if p["is_heading"] and not p["is_empty"]]
    revision_nodes = (
        root.findall(".//w:ins", W_NS)
        + root.findall(".//w:del", W_NS)
        + root.findall(".//w:moveFrom", W_NS)
        + root.findall(".//w:moveTo", W_NS)
    )
    existing_authors = sorted(
        {
            node.attrib.get(w_tag("author"), "")
            for node in revision_nodes
            if node.attrib.get(w_tag("author"))
        }
    )
    comments_root = ET.fromstring(comments_xml) if comments_xml else None
    comment_count = len(comments_root.findall("w:comment", W_NS)) if comments_root is not None else 0
    tables = root.findall(".//w:tbl", W_NS)
    nested_table_count = sum(
        1 for table in tables if has_ancestor(table, w_tag("tbl"), parent_map)
    )
    structure = {
        "table_count": len(tables),
        "nested_table_count": nested_table_count,
        "header_part_count": len(header_parts),
        "footer_part_count": len(footer_parts),
        "textbox_count": len(root.findall(".//w:txbxContent", W_NS)),
        "field_count": len(root.findall(".//w:fldChar", W_NS))
        + len(root.findall(".//w:fldSimple", W_NS)),
        "hyperlink_count": len(root.findall(".//w:hyperlink", W_NS)),
        "drawing_count": len(root.findall(".//w:drawing", W_NS))
        + len(root.findall(".//w:pict", W_NS)),
        "content_control_count": len(root.findall(".//w:sdt", W_NS)),
        "comment_count": comment_count,
        "revision_count": len(revision_nodes),
        "placeholder_paragraph_count": sum(
            1 for paragraph in paragraphs if paragraph["has_placeholder"]
        ),
    }
    risk_flags = [
        name
        for name, active in {
            "existing_revisions": bool(revision_nodes),
            "existing_comments": comment_count > 0,
            "nested_tables": nested_table_count > 0,
            "headers_or_footers": bool(header_parts or footer_parts),
            "textboxes": structure["textbox_count"] > 0,
            "fields": structure["field_count"] > 0,
            "drawings": structure["drawing_count"] > 0,
            "content_controls": structure["content_control_count"] > 0,
            "placeholders": structure["placeholder_paragraph_count"] > 0,
        }.items()
        if active
    ]
    return {
        "ok": True,
        "source": str(docx_path),
        "paragraph_count": len(paragraphs),
        "window": {"start": start_index, "end": end_index, "limit": limit},
        "paragraphs": window,
        "headings": headings,
        "has_existing_revisions": bool(revision_nodes),
        "revision_authors": existing_authors,
        "structure": structure,
        "risk_flags": risk_flags,
    }


@dataclass
class ReplaceParagraphOp:
    paragraph_index: int
    new_text: str


@dataclass
class RenderBlockOp:
    paragraph_index: int
    block_id: str
    original_text: str
    original_text_sha256: str
    new_text: str
    intent_id: str
    dependency_group: str


@dataclass
class ReplaceTextOp:
    paragraph_index: int
    old_text: str
    new_text: str
    occurrence: int = 1
    paragraph_hint: str | None = None
    allow_non_atomic: bool = False
    atomic_reason: str | None = None


@dataclass
class DeleteTextOp:
    paragraph_index: int
    target_text: str
    occurrence: int = 1
    paragraph_hint: str | None = None


@dataclass
class InsertTextOp:
    paragraph_index: int
    anchor_text: str
    text: str
    position: str
    occurrence: int = 1
    paragraph_hint: str | None = None


@dataclass
class AddCommentOp:
    paragraph_index: int
    target_text: str
    comment_text: str
    occurrence: int = 1
    paragraph_hint: str | None = None
    block_id: str | None = None
    original_text: str | None = None
    original_text_sha256: str | None = None
    intent_id: str | None = None
    dependency_group: str | None = None


def load_plan(plan_path: str | None) -> dict[str, Any]:
    if plan_path:
        loaded = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    else:
        raw = sys.stdin.read()
        if not raw.strip():
            fail("apply 需要通过 --plan 或 stdin 提供 JSON 计划。")
        loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        fail("JSON 计划顶层必须是对象。")
    return loaded


def parse_operations(plan: dict[str, Any]) -> list[ReplaceParagraphOp | RenderBlockOp | ReplaceTextOp | DeleteTextOp | InsertTextOp | AddCommentOp]:
    ops = plan.get("operations")
    if not isinstance(ops, list) or not ops:
        fail("计划中的 operations 不能为空。")

    parsed: list[ReplaceParagraphOp | RenderBlockOp | ReplaceTextOp | DeleteTextOp | InsertTextOp | AddCommentOp] = []
    for idx, op in enumerate(ops, start=1):
        if not isinstance(op, dict):
            fail(f"第 {idx} 个 operation 不是对象。")
        op_type = op.get("type")

        locator = op.get("locator", {})
        paragraph_index = op.get("paragraph_index", locator.get("paragraph_index"))
        if not isinstance(paragraph_index, int) or paragraph_index <= 0:
            fail(f"第 {idx} 个 operation 缺少有效的 paragraph_index。")

        occurrence = op.get("occurrence", 1)
        if not isinstance(occurrence, int) or occurrence <= 0:
            fail(f"第 {idx} 个 operation 缺少有效的 occurrence。")

        paragraph_hint = op.get("paragraph_hint")
        if paragraph_hint is not None and not isinstance(paragraph_hint, str):
            fail(f"第 {idx} 个 operation 的 paragraph_hint 必须是字符串。")

        if op_type == "replace_paragraph":
            new_text = op.get("new_text")
            if not isinstance(new_text, str):
                fail(f"第 {idx} 个 operation 缺少字符串类型的 new_text。")
            parsed.append(ReplaceParagraphOp(paragraph_index=paragraph_index, new_text=new_text))
            continue

        if op_type == "render_block":
            locator_block_id = locator.get("block_id")
            original_text = op.get("original_text")
            original_text_sha256 = op.get("original_text_sha256")
            new_text = op.get("new_text")
            intent_id = op.get("intent_id")
            dependency_group = op.get("dependency_group")
            if not isinstance(locator_block_id, str) or not locator_block_id.strip():
                fail(f"第 {idx} 个 render_block 缺少 locator.block_id。")
            if not isinstance(original_text, str) or original_text == "":
                fail(f"第 {idx} 个 render_block 缺少 original_text。")
            if not isinstance(original_text_sha256, str) or original_text_sha256 != sha256_text(original_text):
                fail(
                    f"第 {idx} 个 render_block 的 original_text_sha256 无效。",
                    extra={"error_code": "INVALID_BLOCK_HASH", "operation_index": idx},
                )
            if not isinstance(new_text, str) or new_text == "":
                fail(f"第 {idx} 个 render_block 缺少 new_text。")
            if new_text == original_text:
                fail(f"第 {idx} 个 render_block 修改前后文本相同。")
            if not isinstance(intent_id, str) or not intent_id.strip():
                fail(f"第 {idx} 个 render_block 缺少 intent_id。")
            if not isinstance(dependency_group, str) or not dependency_group.strip():
                fail(f"第 {idx} 个 render_block 缺少 dependency_group。")
            parsed.append(
                RenderBlockOp(
                    paragraph_index=paragraph_index,
                    block_id=locator_block_id,
                    original_text=original_text,
                    original_text_sha256=original_text_sha256,
                    new_text=new_text,
                    intent_id=intent_id,
                    dependency_group=dependency_group,
                )
            )
            continue

        if op_type == "replace_text":
            old_text = op.get("old_text")
            new_text = op.get("new_text")
            if not isinstance(old_text, str) or old_text == "":
                fail(f"第 {idx} 个 operation 缺少字符串类型的 old_text。")
            if not isinstance(new_text, str):
                fail(f"第 {idx} 个 operation 缺少字符串类型的 new_text。")
            if old_text == new_text:
                fail(f"第 {idx} 个 replace_text 修改前后文本相同，无需生成修订。")
            allow_non_atomic_raw = op.get("allow_non_atomic", False)
            if not isinstance(allow_non_atomic_raw, bool):
                fail(f"第 {idx} 个 operation 的 allow_non_atomic 必须是布尔值。")
            allow_non_atomic = allow_non_atomic_raw
            atomic_reason = op.get("atomic_reason")
            if atomic_reason is not None and not isinstance(atomic_reason, str):
                fail(f"第 {idx} 个 operation 的 atomic_reason 必须是字符串。")
            enforce_atomic_replace_text(
                old_text,
                new_text,
                operation_index=idx,
                allow_non_atomic=allow_non_atomic,
                atomic_reason=atomic_reason,
            )
            parsed.append(
                ReplaceTextOp(
                    paragraph_index=paragraph_index,
                    old_text=old_text,
                    new_text=new_text,
                    occurrence=occurrence,
                    paragraph_hint=paragraph_hint,
                    allow_non_atomic=allow_non_atomic,
                    atomic_reason=atomic_reason,
                )
            )
            continue

        if op_type == "delete_text":
            target_text = op.get("target_text") or op.get("old_text")
            if not isinstance(target_text, str) or target_text == "":
                fail(f"第 {idx} 个 operation 缺少字符串类型的 target_text。")
            parsed.append(
                DeleteTextOp(
                    paragraph_index=paragraph_index,
                    target_text=target_text,
                    occurrence=occurrence,
                    paragraph_hint=paragraph_hint,
                )
            )
            continue

        if op_type in {"insert_before", "insert_after"}:
            anchor_text = op.get("anchor_text") or op.get("anchor")
            text = op.get("text")
            if not isinstance(anchor_text, str) or anchor_text == "":
                fail(f"第 {idx} 个 operation 缺少字符串类型的 anchor_text。")
            if not isinstance(text, str) or text == "":
                fail(f"第 {idx} 个 operation 缺少字符串类型的 text。")
            parsed.append(
                InsertTextOp(
                    paragraph_index=paragraph_index,
                    anchor_text=anchor_text,
                    text=text,
                    position="before" if op_type == "insert_before" else "after",
                    occurrence=occurrence,
                    paragraph_hint=paragraph_hint,
                )
            )
            continue

        if op_type == "add_comment":
            target_text = op.get("target_text")
            comment_text = op.get("comment_text")
            if not isinstance(target_text, str) or target_text == "":
                fail(f"第 {idx} 个 operation 缺少字符串类型的 target_text。")
            if not isinstance(comment_text, str) or comment_text == "":
                fail(f"第 {idx} 个 operation 缺少字符串类型的 comment_text。")
            locator_block_id = locator.get("block_id")
            original_text = op.get("original_text")
            original_text_sha256 = op.get("original_text_sha256")
            stable_anchor_values = [locator_block_id, original_text, original_text_sha256]
            if any(value is not None for value in stable_anchor_values):
                if not all(isinstance(value, str) and value for value in stable_anchor_values):
                    fail(
                        f"第 {idx} 个 add_comment 的稳定锚点字段不完整。",
                        extra={"error_code": "INCOMPLETE_BLOCK_ANCHOR", "operation_index": idx},
                    )
                if original_text_sha256 != sha256_text(original_text):
                    fail(
                        f"第 {idx} 个 add_comment 的 original_text_sha256 无效。",
                        extra={"error_code": "INVALID_BLOCK_HASH", "operation_index": idx},
                    )
                if target_text not in original_text:
                    fail(
                        f"第 {idx} 个 add_comment 的 target_text 不在 original_text 中。",
                        extra={"error_code": "INVALID_COMMENT_TARGET", "operation_index": idx},
                    )
            parsed.append(
                AddCommentOp(
                    paragraph_index=paragraph_index,
                    target_text=target_text,
                    comment_text=comment_text,
                    occurrence=occurrence,
                    paragraph_hint=paragraph_hint,
                    block_id=locator_block_id,
                    original_text=original_text,
                    original_text_sha256=original_text_sha256,
                    intent_id=(str(op.get("intent_id")) if op.get("intent_id") is not None else None),
                    dependency_group=(str(op.get("dependency_group")) if op.get("dependency_group") is not None else None),
                )
            )
            continue

        fail(f"暂不支持的 operation type: {op_type}")
    return parsed


def default_revision_author() -> str:
    return DEFAULT_AUTHOR


def update_core_properties(docx_path: Path, *, last_modified_by: str | None, creator: str | None) -> None:
    with ZipFile(docx_path) as zf:
        all_entries = {info.filename: zf.read(info.filename) for info in zf.infolist()}
        infos = list(zf.infolist())

    try:
        core_xml = all_entries["docProps/core.xml"]
    except KeyError:
        return

    root = ET.fromstring(core_xml)
    if creator:
        creator_el = root.find("dc:creator", CORE_NS)
        if creator_el is None:
            creator_el = ET.SubElement(root, f"{{{CORE_NS['dc']}}}creator")
        creator_el.text = creator
    if last_modified_by:
        modified_el = root.find("cp:lastModifiedBy", CORE_NS)
        if modified_el is None:
            modified_el = ET.SubElement(root, f"{{{CORE_NS['cp']}}}lastModifiedBy")
        modified_el.text = last_modified_by

    all_entries["docProps/core.xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    with tempfile.NamedTemporaryFile(prefix="word-redline-core-", suffix=".docx", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        with ZipFile(temp_path, "w") as zout:
            for info in infos:
                zout.writestr(info, all_entries[info.filename])
        shutil.move(temp_path, docx_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def build_initials(author: str) -> str:
    cleaned = re.sub(r"\s+", "", author)
    if cleaned == "":
        return "C"
    if re.search(r"[\u4e00-\u9fff]", cleaned):
        return cleaned[:2]
    letters = [ch for ch in cleaned if ch.isalpha()]
    if not letters:
        return cleaned[:2]
    return "".join(letters[:3]).upper()


def target_review_duration_seconds(paragraph_count: int) -> int:
    if paragraph_count <= 80:
        return 30 * 60
    if paragraph_count <= 200:
        return 45 * 60
    if paragraph_count <= 400:
        return 60 * 60
    return 75 * 60


def operation_text_size(op: Any) -> int:
    if isinstance(op, ReplaceTextOp):
        return len(op.old_text) + len(op.new_text)
    if isinstance(op, ReplaceParagraphOp):
        return len(op.new_text)
    if isinstance(op, RenderBlockOp):
        return len(op.original_text) + len(op.new_text)
    if isinstance(op, DeleteTextOp):
        return len(op.target_text)
    if isinstance(op, InsertTextOp):
        return len(op.anchor_text) + len(op.text)
    if isinstance(op, AddCommentOp):
        return len(op.target_text) + len(op.comment_text)
    return 0


def operation_effort_seconds(op: Any, context_length: int) -> int:
    base = 35
    context_component = min(max(context_length, 0), 500) * 0.35
    text_component = min(operation_text_size(op), 300) * 1.4
    type_component = 0
    if isinstance(op, (ReplaceParagraphOp, RenderBlockOp)):
        type_component = 150
    elif isinstance(op, AddCommentOp):
        type_component = 75
    elif isinstance(op, ReplaceTextOp):
        type_component = 45
    elif isinstance(op, DeleteTextOp):
        type_component = 25
    elif isinstance(op, InsertTextOp):
        type_component = 20
    return max(45, min(360, round(base + context_component + text_component + type_component)))


def build_operation_timestamps(
    operations: list[Any],
    paragraph_texts: list[str],
    *,
    paragraph_count: int,
) -> list[dt.datetime]:
    end_time = dt.datetime.now(LOCAL_TZ).replace(microsecond=0)
    durations: list[int] = []
    natural_variation = (0.92, 1.08, 0.97, 1.13, 0.95, 1.05)
    for index, op in enumerate(operations):
        context = (
            paragraph_texts[op.paragraph_index - 1]
            if 0 < op.paragraph_index <= len(paragraph_texts)
            else ""
        )
        effort = operation_effort_seconds(op, len(context))
        durations.append(
            max(30, round(effort * natural_variation[index % len(natural_variation)]))
        )

    max_duration = target_review_duration_seconds(paragraph_count)
    total_duration = sum(durations)
    if total_duration > max_duration and total_duration > 0:
        scale = max_duration / total_duration
        durations = [max(30, round(duration * scale)) for duration in durations]

    cursor = end_time - dt.timedelta(seconds=sum(durations))
    timestamps: list[dt.datetime] = []
    for duration in durations:
        cursor += dt.timedelta(seconds=duration)
        timestamps.append(cursor)
    return timestamps


def build_timestamp_factory(timestamps: list[dt.datetime]):
    index = {"value": 0}

    def timestamp_factory() -> str:
        if not timestamps:
            return dt.datetime.now(LOCAL_TZ).replace(microsecond=0).isoformat(timespec="seconds")
        position = min(index["value"], len(timestamps) - 1)
        index["value"] += 1
        return timestamps[position].isoformat(timespec="seconds")

    return timestamp_factory


def build_plan_timestamps(
    operations: list[Any],
    paragraph_texts: list[str],
    *,
    paragraph_count: int,
) -> list[dt.datetime]:
    return build_operation_timestamps(
        operations,
        paragraph_texts,
        paragraph_count=paragraph_count,
    )


def next_revision_id(root: ET.Element) -> int:
    max_id = -1
    for tag in ("ins", "del"):
        for elem in root.findall(f".//w:{tag}", W_NS):
            raw = elem.attrib.get(w_tag("id"))
            if raw and raw.isdigit():
                max_id = max(max_id, int(raw))
    return max_id + 1


def nth_occurrence(text: str, needle: str, occurrence: int) -> int:
    start = -1
    pos = 0
    for _ in range(occurrence):
        start = text.find(needle, pos)
        if start < 0:
            return -1
        pos = start + len(needle)
    return start


def resolve_paragraph_index(
    paragraphs: list[ET.Element],
    paragraph_index: int,
    target_text: str,
    paragraph_hint: str | None,
    occurrence: int,
) -> int:
    candidate_index = paragraph_index - 1
    if 0 <= candidate_index < len(paragraphs):
        candidate_text = paragraph_text(paragraphs[candidate_index])
        if nth_occurrence(candidate_text, target_text, occurrence) >= 0 and (
            not paragraph_hint or paragraph_hint in candidate_text
        ):
            return candidate_index

    matches: list[tuple[int, str]] = []
    for idx, paragraph in enumerate(paragraphs):
        text = paragraph_text(paragraph)
        if nth_occurrence(text, target_text, occurrence) < 0:
            continue
        if paragraph_hint and paragraph_hint not in text:
            continue
        matches.append((idx, text))

    if len(matches) == 1:
        return matches[0][0]
    if len(matches) > 1:
        if paragraph_hint:
            scored = sorted(
                (
                    difflib.SequenceMatcher(None, paragraph_hint, text).ratio(),
                    idx,
                )
                for idx, text in matches
            )
            best_score, best_idx = scored[-1]
            second_score = scored[-2][0] if len(scored) > 1 else 0.0
            if best_score >= 0.6 and best_score - second_score >= 0.05:
                return best_idx
        fail(
            f"目标文本存在多处匹配，无法唯一定位: {target_text}",
            extra={"paragraph_index": paragraph_index, "candidate_count": len(matches)},
        )

    if paragraph_hint:
        fallback: list[tuple[float, int]] = []
        for idx, paragraph in enumerate(paragraphs):
            text = paragraph_text(paragraph)
            if nth_occurrence(text, target_text, occurrence) < 0:
                continue
            score = difflib.SequenceMatcher(None, paragraph_hint, text).ratio()
            fallback.append((score, idx))
        if fallback:
            fallback.sort()
            best_score, best_idx = fallback[-1]
            second_score = fallback[-2][0] if len(fallback) > 1 else 0.0
            if best_score >= 0.6 and best_score - second_score >= 0.05:
                return best_idx

    fail(
        f"未找到与目标文本匹配的段落: {target_text}",
        extra={"paragraph_index": paragraph_index, "paragraph_hint": paragraph_hint},
    )


def element_text(element: ET.Element) -> str:
    parts: list[str] = []
    for child in element.iter():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in {"t", "delText"}:
            parts.append(child.text or "")
        elif tag == "tab":
            parts.append("\t")
        elif tag in {"br", "cr"}:
            parts.append("\n")
    return "".join(parts)


def visible_element_text(element: ET.Element) -> str:
    tag = element.tag.rsplit("}", 1)[-1]
    if tag in {"del", "delText"}:
        return ""
    if tag == "t":
        return element.text or ""
    if tag == "tab":
        return "\t"
    if tag in {"br", "cr"}:
        return "\n"
    return "".join(visible_element_text(child) for child in list(element))


def rejected_element_text(element: ET.Element) -> str:
    """Return text as if all tracked revisions in this element were rejected."""
    tag = element.tag.rsplit("}", 1)[-1]
    if tag in {"ins", "moveTo"}:
        return ""
    if tag in {"t", "delText"}:
        return element.text or ""
    if tag == "tab":
        return "\t"
    if tag in {"br", "cr"}:
        return "\n"
    return "".join(rejected_element_text(child) for child in list(element))


def paragraph_rejected_text(paragraph: ET.Element) -> str:
    return rejected_element_text(paragraph).replace("\r", "")


def first_run_properties(paragraph: ET.Element) -> ET.Element | None:
    for run in paragraph.findall(".//w:r", W_NS):
        rpr = run.find("w:rPr", W_NS)
        if rpr is not None:
            return deepcopy(rpr)
    return None


def clone_run_properties(run: ET.Element) -> ET.Element | None:
    rpr = run.find("w:rPr", W_NS)
    if rpr is None:
        return None
    return deepcopy(rpr)


def append_text_nodes(run: ET.Element, text: str, *, deleted: bool) -> None:
    if text == "":
        return

    buffer = ""

    def flush_buffer() -> None:
        nonlocal buffer
        if buffer == "":
            return
        tag = w_tag("delText") if deleted else w_tag("t")
        text_el = ET.SubElement(run, tag)
        if buffer[:1].isspace() or buffer[-1:].isspace() or "  " in buffer:
            text_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        text_el.text = buffer
        buffer = ""

    for char in text:
        if char == "\t":
            flush_buffer()
            ET.SubElement(run, w_tag("tab"))
        elif char == "\n":
            flush_buffer()
            ET.SubElement(run, w_tag("br"))
        else:
            buffer += char
    flush_buffer()


def build_run(text: str, run_props: ET.Element | None) -> ET.Element:
    run = ET.Element(w_tag("r"))
    if run_props is not None:
        run.append(deepcopy(run_props))
    append_text_nodes(run, text, deleted=False)
    return run


@dataclass
class ChildTextSlice:
    element: ET.Element
    text: str
    start: int
    end: int


def paragraph_visible_text_and_children(paragraph: ET.Element) -> tuple[str, list[ChildTextSlice]]:
    pieces: list[str] = []
    slices: list[ChildTextSlice] = []
    pos = 0
    for child in list(paragraph):
        if child.tag == w_tag("pPr"):
            continue
        child_text = visible_element_text(child)
        if child_text == "":
            continue
        end = pos + len(child_text)
        pieces.append(child_text)
        slices.append(ChildTextSlice(child, child_text, pos, end))
        pos = end
    return "".join(pieces), slices


def child_run_properties(child: ET.Element) -> ET.Element | None:
    if child.tag == w_tag("r"):
        return clone_run_properties(child)
    for run in child.findall(".//w:r", W_NS):
        return clone_run_properties(run)
    return None


def narrow_replace_window(original: str, replacement: str) -> tuple[int, int, str]:
    prefix_len = 0
    max_prefix = min(len(original), len(replacement))
    while prefix_len < max_prefix and original[prefix_len] == replacement[prefix_len]:
        prefix_len += 1

    original_suffix = len(original)
    replacement_suffix = len(replacement)
    while (
        original_suffix > prefix_len
        and replacement_suffix > prefix_len
        and original[original_suffix - 1] == replacement[replacement_suffix - 1]
    ):
        original_suffix -= 1
        replacement_suffix -= 1

    return prefix_len, original_suffix, replacement[prefix_len:replacement_suffix]


def replacement_change_segments(original: str, replacement: str) -> list[dict[str, Any]]:
    """
    Return non-equal diff segments, merging adjacent edits that are not separated
    by unchanged text. More than one segment means a replace_text operation is
    carrying multiple independent edits and should normally be split.
    """
    segments: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    matcher = difflib.SequenceMatcher(None, original, replacement, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            if current is not None:
                segments.append(current)
                current = None
            continue
        if current is None:
            current = {
                "old_start": i1,
                "old_end": i2,
                "new_start": j1,
                "new_end": j2,
                "old_text": original[i1:i2],
                "new_text": replacement[j1:j2],
            }
        else:
            current["old_end"] = i2
            current["new_end"] = j2
            current["old_text"] = original[current["old_start"] : i2]
            current["new_text"] = replacement[current["new_start"] : j2]
    if current is not None:
        segments.append(current)
    return segments


def replacement_revision_count(original: str, replacement: str) -> int:
    prefix_len, original_suffix, narrowed_replacement = narrow_replace_window(
        original,
        replacement,
    )
    narrowed_start = prefix_len
    narrowed_end = original_suffix
    if narrowed_start == narrowed_end:
        return 1 if narrowed_replacement else 0
    return 1 + (1 if narrowed_replacement else 0)


def paragraph_revision_count(original: str, replacement: str) -> int:
    count = 0
    matcher = difflib.SequenceMatcher(a=original, b=replacement)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in {"delete", "replace"} and original[i1:i2]:
            count += 1
        if tag in {"insert", "replace"} and replacement[j1:j2]:
            count += 1
    return count


def expected_revision_count(summary: list[dict[str, Any]]) -> int:
    count = 0
    for item in summary:
        item_type = item.get("type")
        if item_type == "replace_text":
            count += replacement_revision_count(
                str(item.get("old_text", "")),
                str(item.get("new_text", "")),
            )
        elif item_type in {"replace_paragraph", "render_block"}:
            count += paragraph_revision_count(
                str(item.get("old_text", "")),
                str(item.get("new_text", "")),
            )
        elif item_type in {"delete_text", "insert_before", "insert_after"}:
            count += 1
    return count


def enforce_atomic_replace_text(
    old_text: str,
    new_text: str,
    *,
    operation_index: int,
    allow_non_atomic: bool,
    atomic_reason: str | None,
) -> None:
    segments = replacement_change_segments(old_text, new_text)
    if len(segments) <= 1:
        return
    if allow_non_atomic:
        if not atomic_reason or not atomic_reason.strip():
            fail(f"第 {operation_index} 个 replace_text 设置了 allow_non_atomic，但缺少 atomic_reason。")
        return

    preview = [
        {
            "old_text": segment["old_text"],
            "new_text": segment["new_text"],
        }
        for segment in segments
    ]
    fail(
        f"第 {operation_index} 个 replace_text 包含 {len(segments)} 个不连续变化，应拆成多个原子 operation。",
        extra={
            "error_code": "NON_ATOMIC_REPLACE",
            "operation_index": operation_index,
            "old_text": old_text,
            "new_text": new_text,
            "change_segments": preview,
            "suggestion": "纯新增用 insert_before/insert_after，纯删除用 delete_text；错字、数字、期限等分别用独立 replace_text。",
        },
    )


def insert_children(parent: ET.Element, index: int, nodes: list[ET.Element]) -> None:
    for offset, node in enumerate(nodes):
        parent.insert(index + offset, node)


def replace_span_with_revisions(
    paragraph: ET.Element,
    start: int,
    end: int,
    replacement: str | None,
    *,
    revision_id: int,
    author: str,
    timestamp_factory,
) -> int:
    para_text, children = paragraph_visible_text_and_children(paragraph)
    affected = [child for child in children if not (child.end <= start or child.start >= end)]
    if not affected:
        fail("目标文本没有落到可编辑文本上。")
    if any(child.element.tag != w_tag("r") for child in affected):
        fail("目标文本位于已有修订、超链接或复杂对象中，无法安全追加文本修订。")

    first = affected[0]
    last = affected[-1]
    prefix = first.text[: max(0, start - first.start)]
    suffix = last.text[max(0, end - last.start) :]
    matched = para_text[start:end]

    new_nodes: list[ET.Element] = []
    prefix_run = build_run(prefix, clone_run_properties(first.element)) if prefix else None
    if prefix_run is not None:
        new_nodes.append(prefix_run)

    revision_timestamp = timestamp_factory()
    del_node = build_revision(
        matched,
        clone_run_properties(first.element),
        revision_type="del",
        revision_id=revision_id,
        author=author,
        timestamp=revision_timestamp,
    )
    new_nodes.append(del_node)
    revision_id += 1

    if replacement:
        ins_node = build_revision(
            replacement,
            clone_run_properties(first.element),
            revision_type="ins",
            revision_id=revision_id,
            author=author,
            timestamp=revision_timestamp,
        )
        new_nodes.append(ins_node)
        revision_id += 1

    suffix_run = build_run(suffix, clone_run_properties(last.element)) if suffix else None
    if suffix_run is not None:
        new_nodes.append(suffix_run)

    paragraph_children = list(paragraph)
    insert_at = paragraph_children.index(first.element)
    for child in affected:
        paragraph.remove(child.element)
    insert_children(paragraph, insert_at, new_nodes)
    return revision_id


def replace_text_minimal(
    paragraph: ET.Element,
    target_text: str,
    replacement: str,
    *,
    occurrence: int,
    revision_id: int,
    author: str,
    timestamp_factory,
) -> int:
    para_text, _children = paragraph_visible_text_and_children(paragraph)
    start = nth_occurrence(para_text, target_text, occurrence)
    if start < 0:
        fail(f"未找到待替换文本: {target_text}")
    end = start + len(target_text)

    prefix_len, original_suffix, narrowed_replacement = narrow_replace_window(target_text, replacement)
    if prefix_len == len(target_text) and prefix_len == len(replacement):
        return revision_id

    narrowed_start = start + prefix_len
    narrowed_end = start + original_suffix
    if narrowed_start == narrowed_end:
        if not narrowed_replacement:
            return revision_id
        return insert_text_at_position(
            paragraph,
            narrowed_start,
            narrowed_replacement,
            revision_id=revision_id,
            author=author,
            timestamp_factory=timestamp_factory,
        )
    return replace_span_with_revisions(
        paragraph,
        narrowed_start,
        narrowed_end,
        narrowed_replacement,
        revision_id=revision_id,
        author=author,
        timestamp_factory=timestamp_factory,
    )


def insert_text_at_position(
    paragraph: ET.Element,
    insert_pos: int,
    text: str,
    *,
    revision_id: int,
    author: str,
    timestamp_factory,
) -> int:
    visible_text, visible_children = paragraph_visible_text_and_children(paragraph)
    if not visible_children:
        fail("段落中没有可编辑文本")
    if insert_pos < 0 or insert_pos > len(visible_text):
        fail(f"插入位置越界: {insert_pos}")

    target_child = next((child for child in visible_children if child.start <= insert_pos <= child.end), None)
    if target_child is None:
        target_child = visible_children[-1]

    children = list(paragraph)
    target_index = children.index(target_child.element)

    if target_child.element.tag == w_tag("r"):
        ins_node = build_revision(
            text,
            clone_run_properties(target_child.element),
            revision_type="ins",
            revision_id=revision_id,
            author=author,
            timestamp=timestamp_factory(),
        )

        if insert_pos == len(visible_text):
            insert_children(paragraph, target_index + 1, [ins_node])
            return revision_id + 1
        if insert_pos == target_child.start:
            insert_children(paragraph, target_index, [ins_node])
            return revision_id + 1
        if insert_pos == target_child.end:
            insert_children(paragraph, target_index + 1, [ins_node])
            return revision_id + 1

        offset = insert_pos - target_child.start
        prefix = target_child.text[:offset]
        suffix = target_child.text[offset:]
        prefix_run = build_run(prefix, clone_run_properties(target_child.element)) if prefix else None
        suffix_run = build_run(suffix, clone_run_properties(target_child.element)) if suffix else None
        nodes = [node for node in [prefix_run, ins_node, suffix_run] if node is not None]
        paragraph.remove(target_child.element)
        insert_children(paragraph, target_index, nodes)
        return revision_id + 1

    ins_node = build_revision(
        text,
        child_run_properties(target_child.element),
        revision_type="ins",
        revision_id=revision_id,
        author=author,
        timestamp=timestamp_factory(),
    )

    if insert_pos == len(visible_text):
        insert_children(paragraph, target_index + 1, [ins_node])
        return revision_id + 1
    if insert_pos == target_child.start:
        insert_children(paragraph, target_index, [ins_node])
        return revision_id + 1
    if insert_pos == target_child.end:
        insert_children(paragraph, target_index + 1, [ins_node])
        return revision_id + 1

    fail("插入位置位于已有修订或复杂对象内部，当前仅支持在其边界处插入。")


def insert_text_at_anchor(
    paragraph: ET.Element,
    anchor_text: str,
    text: str,
    *,
    position: str,
    occurrence: int,
    revision_id: int,
    author: str,
    timestamp_factory,
) -> int:
    visible_text = paragraph_text(paragraph)
    anchor_start = nth_occurrence(visible_text, anchor_text, occurrence)
    if anchor_start < 0:
        fail(f"未找到插入锚点: {anchor_text}")
    insert_pos = anchor_start if position == "before" else anchor_start + len(anchor_text)
    return insert_text_at_position(
        paragraph,
        insert_pos,
        text,
        revision_id=revision_id,
        author=author,
        timestamp_factory=timestamp_factory,
    )


def build_revision(text: str, run_props: ET.Element | None, *, revision_type: str, revision_id: int, author: str, timestamp: str) -> ET.Element:
    rev = ET.Element(
        w_tag(revision_type),
        {
            w_tag("id"): str(revision_id),
            w_tag("author"): author,
            w_tag("date"): timestamp,
        },
    )
    run = ET.SubElement(rev, w_tag("r"))
    if run_props is not None:
        run.append(deepcopy(run_props))
    append_text_nodes(run, text, deleted=(revision_type == "del"))
    return rev


def ensure_comments_part(
    all_entries: dict[str, bytes],
    infos: list[Any],
) -> tuple[ET.Element, ET.Element, ET.Element]:
    if "[Content_Types].xml" in all_entries:
        content_types_root = ET.fromstring(all_entries["[Content_Types].xml"])
    else:
        fail("文档缺少 [Content_Types].xml，无法添加批注。")

    if "word/_rels/document.xml.rels" in all_entries:
        rels_root = ET.fromstring(all_entries["word/_rels/document.xml.rels"])
    else:
        fail("文档缺少 word/_rels/document.xml.rels，无法添加批注。")

    if "word/comments.xml" in all_entries:
        comments_root = ET.fromstring(all_entries["word/comments.xml"])
    else:
        comments_root = ET.Element(w_tag("comments"))
        all_entries["word/comments.xml"] = ET.tostring(comments_root, encoding="utf-8", xml_declaration=True)
        if not any(getattr(info, "filename", "") == "word/comments.xml" for info in infos):
            infos.append("word/comments.xml")

    return content_types_root, rels_root, comments_root


def next_comment_id(comments_root: ET.Element) -> int:
    max_id = -1
    for comment in comments_root.findall("w:comment", W_NS):
        raw = comment.attrib.get(w_tag("id"))
        if raw and raw.isdigit():
            max_id = max(max_id, int(raw))
    return max_id + 1


def next_relationship_id(rels_root: ET.Element) -> str:
    max_id = 0
    id_attr = "{http://schemas.openxmlformats.org/package/2006/relationships}Id"
    for rel in rels_root.findall("pr:Relationship", PKG_REL_NS):
        raw = rel.attrib.get("Id") or rel.attrib.get(id_attr) or ""
        match = re.fullmatch(r"rId(\d+)", raw)
        if match:
            max_id = max(max_id, int(match.group(1)))
    return f"rId{max_id + 1}"


def ensure_comments_relationship(rels_root: ET.Element) -> None:
    rel_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
    for rel in rels_root.findall("pr:Relationship", PKG_REL_NS):
        if rel.attrib.get("Type") == rel_type:
            return
    ET.SubElement(
        rels_root,
        "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship",
        {
            "Id": next_relationship_id(rels_root),
            "Type": rel_type,
            "Target": "comments.xml",
        },
    )


def ensure_comments_content_type(content_types_root: ET.Element) -> None:
    override_tag = "{http://schemas.openxmlformats.org/package/2006/content-types}Override"
    for override in content_types_root.findall("ct:Override", CONTENT_TYPES_NS):
        if override.attrib.get("PartName") == "/word/comments.xml":
            return
    ET.SubElement(
        content_types_root,
        override_tag,
        {
            "PartName": "/word/comments.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
        },
    )


def build_comment(comment_id: int, comment_text: str, *, author: str, initials: str, timestamp: str) -> ET.Element:
    comment = ET.Element(
        w_tag("comment"),
        {
            w_tag("id"): str(comment_id),
            w_tag("author"): author,
            w_tag("initials"): initials,
            w_tag("date"): timestamp,
        },
    )
    paragraph = ET.SubElement(comment, w_tag("p"))
    run = ET.SubElement(paragraph, w_tag("r"))
    append_text_nodes(run, comment_text, deleted=False)
    return comment


def comment_reference_run(comment_id: int) -> ET.Element:
    run = ET.Element(w_tag("r"))
    ET.SubElement(run, w_tag("commentReference"), {w_tag("id"): str(comment_id)})
    return run


def text_child_ranges(paragraph: ET.Element) -> tuple[list[ET.Element], list[tuple[int, int, int, str]], str]:
    children = list(paragraph)
    ranges: list[tuple[int, int, int, str]] = []
    cursor = 0
    for idx, child in enumerate(children):
        if child.tag == w_tag("pPr"):
            continue
        text = visible_element_text(child)
        if text == "":
            continue
        start = cursor
        end = cursor + len(text)
        ranges.append((idx, start, end, text))
        cursor = end
    return children, ranges, "".join(item[3] for item in ranges)


def split_run_child_at(paragraph: ET.Element, child_index: int, offset: int) -> None:
    children = list(paragraph)
    try:
        child = children[child_index]
    except IndexError:
        fail(f"批注定位失败：子节点索引越界 {child_index}。")
    text = element_text(child)
    if offset <= 0 or offset >= len(text):
        return
    if child.tag != w_tag("r"):
        fail("目标文本位于复杂对象中，当前仅支持在普通文本 run 内精确添加批注。")

    run_props = child.find("w:rPr", W_NS)
    before = build_run(text[:offset], run_props)
    after = build_run(text[offset:], run_props)
    paragraph.remove(child)
    paragraph.insert(child_index, before)
    paragraph.insert(child_index + 1, after)


def add_comment_to_paragraph(
    paragraph: ET.Element,
    target_text: str,
    comment_id: int,
    *,
    occurrence: int,
) -> None:
    children, ranges, full_text = text_child_ranges(paragraph)
    if not children:
        fail("目标段落为空，无法添加批注。")

    target_start = nth_occurrence(full_text, target_text, occurrence)
    if target_start < 0:
        fail(f"未找到可直接添加批注的目标文本: {target_text}")
    target_end = target_start + len(target_text)

    start_range = next(((idx, start, end, text) for idx, start, end, text in ranges if start <= target_start < end), None)
    end_range = next(((idx, start, end, text) for idx, start, end, text in ranges if start < target_end <= end), None)
    if start_range is None or end_range is None:
        fail(f"未能定位批注范围: {target_text}")

    end_child_index, end_child_start, end_child_end, _end_text = end_range
    if target_end < end_child_end:
        split_run_child_at(paragraph, end_child_index, target_end - end_child_start)

    _children, ranges, _full_text = text_child_ranges(paragraph)
    start_range = next(((idx, start, end, text) for idx, start, end, text in ranges if start <= target_start < end), None)
    if start_range is None:
        fail(f"未能定位批注起始位置: {target_text}")

    start_child_index, start_child_start, start_child_end, _start_text = start_range
    if target_start > start_child_start:
        split_run_child_at(paragraph, start_child_index, target_start - start_child_start)

    _children, ranges, _full_text = text_child_ranges(paragraph)
    covered_ranges = [
        (idx, start, end, text)
        for idx, start, end, text in ranges
        if end > target_start and start < target_end and start >= target_start and end <= target_end
    ]
    if not covered_ranges:
        fail(f"未能生成批注锚点: {target_text}")

    target_start_index = covered_ranges[0][0]
    target_end_index = covered_ranges[-1][0]

    start_marker = ET.Element(w_tag("commentRangeStart"), {w_tag("id"): str(comment_id)})
    end_marker = ET.Element(w_tag("commentRangeEnd"), {w_tag("id"): str(comment_id)})

    paragraph.insert(target_start_index, start_marker)
    paragraph.insert(target_end_index + 2, end_marker)
    paragraph.insert(target_end_index + 3, comment_reference_run(comment_id))


def apply_comments(
    docx_path: Path,
    ops: list[AddCommentOp],
    *,
    author: str,
    initials: str,
    timestamp_factory,
) -> dict[str, Any]:
    with ZipFile(docx_path) as zf:
        try:
            document_xml = zf.read("word/document.xml")
        except KeyError:
            fail("文档缺少 word/document.xml，无法添加批注。")
        all_entries = {info.filename: zf.read(info.filename) for info in zf.infolist()}
        infos = list(zf.infolist())

    root = ET.fromstring(document_xml)
    body = root.find("w:body", W_NS)
    if body is None:
        fail("文档 body 为空，无法添加批注。")
    paragraphs = document_paragraphs(body)

    content_types_root, rels_root, comments_root = ensure_comments_part(all_entries, infos)
    ensure_comments_relationship(rels_root)
    ensure_comments_content_type(content_types_root)

    comment_id = next_comment_id(comments_root)
    summary: list[dict[str, Any]] = []

    for op in ops:
        if op.block_id and op.original_text and op.original_text_sha256:
            resolved_index = resolve_anchored_block(
                paragraphs,
                paragraph_index=op.paragraph_index,
                expected_block_id=op.block_id,
                expected_text=op.original_text,
                expected_text_sha256=op.original_text_sha256,
                intent_id=op.intent_id,
                dependency_group=op.dependency_group,
            )
        else:
            resolved_index = resolve_paragraph_index(
                paragraphs,
                op.paragraph_index,
                op.target_text,
                op.paragraph_hint,
                op.occurrence,
            )
        paragraph = paragraphs[resolved_index]
        if nth_occurrence(paragraph_text(paragraph), op.target_text, op.occurrence) < 0:
            fail(
                f"第 {op.paragraph_index} 段未找到第 {op.occurrence} 处批注目标文本: {op.target_text}",
                extra={"paragraph_text": paragraph_text(paragraph)},
            )

        add_comment_to_paragraph(paragraph, op.target_text, comment_id, occurrence=op.occurrence)
        comments_root.append(
            build_comment(
                comment_id,
                op.comment_text,
                author=author,
                initials=initials,
                timestamp=timestamp_factory(),
            )
        )
        summary.append(
            {
                "type": "add_comment",
                "paragraph_index": resolved_index + 1,
                "target_text": op.target_text,
                "comment_text": op.comment_text,
                "comment_id": comment_id,
                **({"block_id": op.block_id} if op.block_id else {}),
                **({"intent_id": op.intent_id} if op.intent_id else {}),
                **({"dependency_group": op.dependency_group} if op.dependency_group else {}),
            }
        )
        comment_id += 1

    all_entries["word/document.xml"] = serialize_word_document(root)
    all_entries["word/comments.xml"] = ET.tostring(comments_root, encoding="utf-8", xml_declaration=True)
    all_entries["word/_rels/document.xml.rels"] = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)
    all_entries["[Content_Types].xml"] = ET.tostring(content_types_root, encoding="utf-8", xml_declaration=True)

    with tempfile.NamedTemporaryFile(prefix="word-redline-", suffix=".docx", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        with ZipFile(temp_path, "w") as zout:
            seen_comments = False
            for info in infos:
                filename = getattr(info, "filename", info)
                if filename == "word/comments.xml":
                    seen_comments = True
                zout.writestr(info, all_entries[filename])
            if not seen_comments and "word/comments.xml" in all_entries:
                zout.writestr("word/comments.xml", all_entries["word/comments.xml"])
        shutil.move(temp_path, docx_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return {"operation_count": len(ops), "summary": summary}


def replace_paragraph_with_diff(
    paragraph: ET.Element,
    old_text: str,
    new_text: str,
    *,
    start_revision_id: int,
    author: str,
    timestamp: str,
) -> int:
    ppr = paragraph.find("w:pPr", W_NS)
    preserved_ppr = deepcopy(ppr) if ppr is not None else None
    run_props = first_run_properties(paragraph)

    for child in list(paragraph):
        paragraph.remove(child)
    if preserved_ppr is not None:
        paragraph.append(preserved_ppr)

    revision_id = start_revision_id
    matcher = difflib.SequenceMatcher(a=old_text, b=new_text)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            segment = old_text[i1:i2]
            if segment:
                paragraph.append(build_run(segment, run_props))
            continue
        if tag in {"delete", "replace"}:
            deleted = old_text[i1:i2]
            if deleted:
                paragraph.append(
                    build_revision(
                        deleted,
                        run_props,
                        revision_type="del",
                        revision_id=revision_id,
                        author=author,
                        timestamp=timestamp,
                    )
                )
                revision_id += 1
        if tag in {"insert", "replace"}:
            inserted = new_text[j1:j2]
            if inserted:
                paragraph.append(
                    build_revision(
                        inserted,
                        run_props,
                        revision_type="ins",
                        revision_id=revision_id,
                        author=author,
                        timestamp=timestamp,
                    )
                )
                revision_id += 1
    return revision_id


def ensure_safe_paragraph_rewrite(paragraph: ET.Element, paragraph_index: int) -> None:
    allowed_paragraph_children = {w_tag("pPr"), w_tag("r")}
    unsupported_children = [
        child.tag.rsplit("}", 1)[-1]
        for child in list(paragraph)
        if child.tag not in allowed_paragraph_children
    ]
    if unsupported_children:
        fail(
            f"第 {paragraph_index} 段包含已有修订、超链接或复杂对象，不能安全整段重写。",
            extra={"unsupported_children": sorted(set(unsupported_children))},
        )

    run_property_variants = {
        ET.tostring(run.find("w:rPr", W_NS), encoding="unicode")
        if run.find("w:rPr", W_NS) is not None
        else ""
        for run in paragraph.findall("w:r", W_NS)
        if element_text(run)
    }
    if len(run_property_variants) > 1:
        fail(
            f"第 {paragraph_index} 段包含混合文字格式，不能安全整段重写；请改用小粒度 operation。",
        )


def resolve_anchored_block(
    paragraphs: list[ET.Element],
    *,
    paragraph_index: int,
    expected_block_id: str,
    expected_text: str,
    expected_text_sha256: str,
    intent_id: str | None,
    dependency_group: str | None,
) -> int:
    candidate_index = paragraph_index - 1
    if not 0 <= candidate_index < len(paragraphs):
        fail(
            f"稳定锚点段落索引越界: {paragraph_index}",
            extra={
                "error_code": "BLOCK_INDEX_OUT_OF_RANGE",
                "block_id": expected_block_id,
                "intent_id": intent_id,
                "dependency_group": dependency_group,
            },
        )
    current_text = paragraph_text(paragraphs[candidate_index])
    current_hash = sha256_text(current_text)
    current_block_id = block_id(paragraph_index, current_text)
    if (
        current_text != expected_text
        or current_hash != expected_text_sha256
        or current_block_id != expected_block_id
    ):
        fail(
            f"稳定锚点与当前段落不一致: {expected_block_id}",
            extra={
                "error_code": "BLOCK_ANCHOR_MISMATCH",
                "paragraph_index": paragraph_index,
                "block_id": expected_block_id,
                "current_block_id": current_block_id,
                "expected_text_sha256": expected_text_sha256,
                "current_text_sha256": current_hash,
                "intent_id": intent_id,
                "dependency_group": dependency_group,
            },
        )
    return candidate_index


def apply_render_block_redlines(
    docx_path: Path,
    ops: list[RenderBlockOp],
    *,
    author: str,
    timestamp_factory,
) -> dict[str, Any]:
    """Render each anchored paragraph exactly once from immutable source text."""
    with ZipFile(docx_path) as zf:
        try:
            document_xml = zf.read("word/document.xml")
        except KeyError:
            fail("文档缺少 word/document.xml，无法应用段落渲染。")
        all_entries = {info.filename: zf.read(info.filename) for info in zf.infolist()}
        infos = list(zf.infolist())

    root = ET.fromstring(document_xml)
    body = root.find("w:body", W_NS)
    if body is None:
        fail("文档 body 为空，无法应用段落渲染。")

    paragraphs = document_paragraphs(body)
    revision_id = next_revision_id(root)
    summary: list[dict[str, Any]] = []
    seen_blocks: set[str] = set()

    for op in ops:
        if op.block_id in seen_blocks:
            fail(
                f"同一计划重复渲染 block: {op.block_id}",
                extra={"error_code": "DUPLICATE_BLOCK_RENDER", "block_id": op.block_id},
            )
        seen_blocks.add(op.block_id)
        resolved_index = resolve_anchored_block(
            paragraphs,
            paragraph_index=op.paragraph_index,
            expected_block_id=op.block_id,
            expected_text=op.original_text,
            expected_text_sha256=op.original_text_sha256,
            intent_id=op.intent_id,
            dependency_group=op.dependency_group,
        )
        paragraph = paragraphs[resolved_index]
        ensure_safe_paragraph_rewrite(paragraph, op.paragraph_index)
        revision_id = replace_paragraph_with_diff(
            paragraph,
            op.original_text,
            op.new_text,
            start_revision_id=revision_id,
            author=author,
            timestamp=timestamp_factory(),
        )
        summary.append(
            {
                "type": "render_block",
                "paragraph_index": op.paragraph_index,
                "block_id": op.block_id,
                "intent_id": op.intent_id,
                "dependency_group": op.dependency_group,
                "old_text": op.original_text,
                "new_text": op.new_text,
            }
        )

    all_entries["word/document.xml"] = serialize_word_document(root)
    with tempfile.NamedTemporaryFile(prefix="word-redline-block-", suffix=".docx", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        with ZipFile(temp_path, "w") as zout:
            for info in infos:
                zout.writestr(info, all_entries[info.filename])
        shutil.move(temp_path, docx_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    return {"operation_count": len(ops), "summary": summary}


def apply_text_redlines(
    docx_path: Path,
    ops: list[ReplaceTextOp],
    *,
    author: str,
    timestamp_factory,
) -> dict[str, Any]:
    with ZipFile(docx_path) as zf:
        try:
            document_xml = zf.read("word/document.xml")
        except KeyError:
            fail("文档缺少 word/document.xml，无法应用文本修订。")
        all_entries = {info.filename: zf.read(info.filename) for info in zf.infolist()}
        infos = list(zf.infolist())

    root = ET.fromstring(document_xml)
    body = root.find("w:body", W_NS)
    if body is None:
        fail("文档 body 为空，无法应用文本修订。")

    paragraphs = document_paragraphs(body)
    revision_id = next_revision_id(root)
    summary: list[dict[str, Any]] = []

    for op in ops:
        resolved_index = resolve_paragraph_index(
            paragraphs,
            op.paragraph_index,
            op.old_text,
            op.paragraph_hint,
            op.occurrence,
        )
        paragraph = paragraphs[resolved_index]
        old_paragraph_text = paragraph_text(paragraph)
        if nth_occurrence(old_paragraph_text, op.old_text, op.occurrence) < 0:
            fail(
                f"第 {op.paragraph_index} 段未找到第 {op.occurrence} 处待替换文本: {op.old_text}",
                extra={"paragraph_text": old_paragraph_text},
            )
        revision_id = replace_text_minimal(
            paragraph,
            op.old_text,
            op.new_text,
            occurrence=op.occurrence,
            revision_id=revision_id,
            author=author,
            timestamp_factory=timestamp_factory,
        )
        summary.append(
            {
                "type": "replace_text",
                "paragraph_index": resolved_index + 1,
                "old_text": op.old_text,
                "new_text": op.new_text,
                **(
                    {"allow_non_atomic": True, "atomic_reason": op.atomic_reason}
                    if op.allow_non_atomic
                    else {}
                ),
            }
        )

    all_entries["word/document.xml"] = serialize_word_document(root)

    with tempfile.NamedTemporaryFile(prefix="word-redline-", suffix=".docx", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        with ZipFile(temp_path, "w") as zout:
            for info in infos:
                zout.writestr(info, all_entries[info.filename])
        shutil.move(temp_path, docx_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return {
        "operation_count": len(ops),
        "summary": summary,
    }


def apply_delete_redlines(
    docx_path: Path,
    ops: list[DeleteTextOp],
    *,
    author: str,
    timestamp_factory,
) -> dict[str, Any]:
    with ZipFile(docx_path) as zf:
        try:
            document_xml = zf.read("word/document.xml")
        except KeyError:
            fail("文档缺少 word/document.xml，无法应用删除修订。")
        all_entries = {info.filename: zf.read(info.filename) for info in zf.infolist()}
        infos = list(zf.infolist())

    root = ET.fromstring(document_xml)
    body = root.find("w:body", W_NS)
    if body is None:
        fail("文档 body 为空，无法应用删除修订。")

    paragraphs = document_paragraphs(body)
    revision_id = next_revision_id(root)
    summary: list[dict[str, Any]] = []

    for op in ops:
        resolved_index = resolve_paragraph_index(
            paragraphs,
            op.paragraph_index,
            op.target_text,
            op.paragraph_hint,
            op.occurrence,
        )
        paragraph = paragraphs[resolved_index]
        if nth_occurrence(paragraph_text(paragraph), op.target_text, op.occurrence) < 0:
            fail(
                f"第 {op.paragraph_index} 段未找到第 {op.occurrence} 处待删除文本: {op.target_text}",
                extra={"paragraph_text": paragraph_text(paragraph)},
            )
        revision_id = replace_text_minimal(
            paragraph,
            op.target_text,
            "",
            occurrence=op.occurrence,
            revision_id=revision_id,
            author=author,
            timestamp_factory=timestamp_factory,
        )
        summary.append(
            {
                "type": "delete_text",
                "paragraph_index": resolved_index + 1,
                "target_text": op.target_text,
            }
        )

    all_entries["word/document.xml"] = serialize_word_document(root)

    with tempfile.NamedTemporaryFile(prefix="word-redline-", suffix=".docx", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        with ZipFile(temp_path, "w") as zout:
            for info in infos:
                zout.writestr(info, all_entries[info.filename])
        shutil.move(temp_path, docx_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return {"operation_count": len(ops), "summary": summary}


def apply_insert_redlines(
    docx_path: Path,
    ops: list[InsertTextOp],
    *,
    author: str,
    timestamp_factory,
) -> dict[str, Any]:
    with ZipFile(docx_path) as zf:
        try:
            document_xml = zf.read("word/document.xml")
        except KeyError:
            fail("文档缺少 word/document.xml，无法应用插入修订。")
        all_entries = {info.filename: zf.read(info.filename) for info in zf.infolist()}
        infos = list(zf.infolist())

    root = ET.fromstring(document_xml)
    body = root.find("w:body", W_NS)
    if body is None:
        fail("文档 body 为空，无法应用插入修订。")

    paragraphs = document_paragraphs(body)
    revision_id = next_revision_id(root)
    summary: list[dict[str, Any]] = []

    for op in ops:
        resolved_index = resolve_paragraph_index(
            paragraphs,
            op.paragraph_index,
            op.anchor_text,
            op.paragraph_hint,
            op.occurrence,
        )
        paragraph = paragraphs[resolved_index]
        if nth_occurrence(paragraph_text(paragraph), op.anchor_text, op.occurrence) < 0:
            fail(
                f"第 {op.paragraph_index} 段未找到第 {op.occurrence} 处插入锚点: {op.anchor_text}",
                extra={"paragraph_text": paragraph_text(paragraph)},
            )
        revision_id = insert_text_at_anchor(
            paragraph,
            op.anchor_text,
            op.text,
            position=op.position,
            occurrence=op.occurrence,
            revision_id=revision_id,
            author=author,
            timestamp_factory=timestamp_factory,
        )
        summary.append(
            {
                "type": "insert_before" if op.position == "before" else "insert_after",
                "paragraph_index": resolved_index + 1,
                "anchor_text": op.anchor_text,
                "text": op.text,
            }
        )

    all_entries["word/document.xml"] = serialize_word_document(root)

    with tempfile.NamedTemporaryFile(prefix="word-redline-", suffix=".docx", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        with ZipFile(temp_path, "w") as zout:
            for info in infos:
                zout.writestr(info, all_entries[info.filename])
        shutil.move(temp_path, docx_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return {"operation_count": len(ops), "summary": summary}


def apply_paragraph_redlines(docx_path: Path, ops: list[ReplaceParagraphOp], *, author: str, timestamp_factory) -> dict[str, Any]:
    with ZipFile(docx_path) as zf:
        try:
            document_xml = zf.read("word/document.xml")
        except KeyError:
            fail("文档缺少 word/document.xml，无法应用整段修订。")
        all_entries = {info.filename: zf.read(info.filename) for info in zf.infolist()}
        infos = list(zf.infolist())

    root = ET.fromstring(document_xml)
    body = root.find("w:body", W_NS)
    if body is None:
        fail("文档 body 为空，无法应用整段修订。")

    paragraphs = document_paragraphs(body)
    revision_id = next_revision_id(root)
    summary: list[dict[str, Any]] = []

    for op in ops:
        try:
            paragraph = paragraphs[op.paragraph_index - 1]
        except IndexError:
            fail(f"段落索引越界: {op.paragraph_index}，文档共 {len(paragraphs)} 段。")
        ensure_safe_paragraph_rewrite(paragraph, op.paragraph_index)
        old_paragraph_text = paragraph_text(paragraph)
        if old_paragraph_text == op.new_text:
            fail(f"第 {op.paragraph_index} 段修改前后文本相同，无需生成修订。")
        revision_id = replace_paragraph_with_diff(
            paragraph,
            old_paragraph_text,
            op.new_text,
            start_revision_id=revision_id,
            author=author,
            timestamp=timestamp_factory(),
        )
        summary.append(
            {
                "type": "replace_paragraph",
                "paragraph_index": op.paragraph_index,
                "old_text": old_paragraph_text,
                "new_text": op.new_text,
            }
        )

    all_entries["word/document.xml"] = serialize_word_document(root)

    with tempfile.NamedTemporaryFile(prefix="word-redline-", suffix=".docx", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        with ZipFile(temp_path, "w") as zout:
            for info in infos:
                zout.writestr(info, all_entries[info.filename])
        shutil.move(temp_path, docx_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return {
        "operation_count": len(ops),
        "summary": summary,
    }


def apply_plan(plan_path: str | None) -> dict[str, Any]:
    plan = load_plan(plan_path)

    source_value = plan.get("source")
    if not isinstance(source_value, str) or not source_value.strip():
        fail("计划中的 source 必须是非空路径字符串。")
    source = Path(source_value)
    ensure_docx(source)
    expected_source_sha256 = plan.get("source_sha256")
    if expected_source_sha256 is not None:
        if not isinstance(expected_source_sha256, str) or not expected_source_sha256.strip():
            fail("source_sha256 必须是非空字符串。", extra={"error_code": "INVALID_SOURCE_HASH"})
        actual_source_sha256 = sha256_file(source)
        if actual_source_sha256 != expected_source_sha256:
            fail(
                "源文件已在计划生成后发生变化，拒绝应用旧计划。",
                extra={
                    "error_code": "SOURCE_CHANGED",
                    "expected_source_sha256": expected_source_sha256,
                    "actual_source_sha256": actual_source_sha256,
                },
            )
    operations = parse_operations(plan)

    inspect_payload = inspect_docx(source, start=1, limit=0)
    para_count = inspect_payload["paragraph_count"]
    bad_indices = [op.paragraph_index for op in operations if op.paragraph_index > para_count]
    if bad_indices:
        fail(f"段落索引越界: {bad_indices}，文档共 {para_count} 段。")

    requested_in_place = plan.get("in_place")
    if requested_in_place is not None and not isinstance(requested_in_place, bool):
        fail("in_place 必须是布尔值。")

    output_value = plan.get("output")
    if output_value is not None and (
        not isinstance(output_value, str) or not output_value.strip()
    ):
        fail("output 必须是非空路径字符串。")
    if requested_in_place is False and not output_value:
        fail("in_place 为 false 时必须提供 output。")
    output = Path(output_value) if output_value else source
    if output.suffix.lower() != ".docx":
        fail(f"输出文件必须是 .docx: {output}")
    in_place = output.resolve() == source.resolve()
    if requested_in_place is True and not in_place:
        fail("in_place 为 true 时，output 必须省略或与 source 相同。")
    if not in_place and output.exists():
        fail(f"输出文件已存在: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    author = str(plan.get("author") or default_revision_author())
    initials = str(plan.get("initials") or build_initials(author))
    paragraph_texts = [paragraph["text"] for paragraph in inspect_payload["paragraphs"]]
    timestamps = build_plan_timestamps(
        operations,
        paragraph_texts,
        paragraph_count=para_count,
    )
    timestamp_factory = build_timestamp_factory(timestamps)

    pre_verify = verify_docx(source)
    with tempfile.NamedTemporaryFile(
        prefix=f".{source.stem}-redline-",
        suffix=".docx",
        dir=output.parent,
        delete=False,
    ) as tmp:
        staged_output = Path(tmp.name)

    summary: list[dict[str, Any]] = []
    committed = False
    try:
        shutil.copy2(source, staged_output)
        for op in operations:
            if isinstance(op, ReplaceTextOp):
                result = apply_text_redlines(
                    staged_output,
                    [op],
                    author=author,
                    timestamp_factory=timestamp_factory,
                )
            elif isinstance(op, DeleteTextOp):
                result = apply_delete_redlines(
                    staged_output,
                    [op],
                    author=author,
                    timestamp_factory=timestamp_factory,
                )
            elif isinstance(op, InsertTextOp):
                result = apply_insert_redlines(
                    staged_output,
                    [op],
                    author=author,
                    timestamp_factory=timestamp_factory,
                )
            elif isinstance(op, ReplaceParagraphOp):
                result = apply_paragraph_redlines(
                    staged_output,
                    [op],
                    author=author,
                    timestamp_factory=timestamp_factory,
                )
            elif isinstance(op, RenderBlockOp):
                result = apply_render_block_redlines(
                    staged_output,
                    [op],
                    author=author,
                    timestamp_factory=timestamp_factory,
                )
            elif isinstance(op, AddCommentOp):
                result = apply_comments(
                    staged_output,
                    [op],
                    author=author,
                    initials=initials,
                    timestamp_factory=timestamp_factory,
                )
            else:
                fail(f"无法执行的 operation: {type(op).__name__}")
            summary.extend(result["summary"])

        update_core_properties(
            staged_output,
            last_modified_by=str(plan.get("last_modified_by") or author),
            creator=(
                str(plan["creator"])
                if "creator" in plan and plan.get("creator") is not None
                else None
            ),
        )

        verify_payload = verify_docx(staged_output)
        revision_delta = verify_payload["total_revisions"] - pre_verify["total_revisions"]
        comment_delta = verify_payload["comments"] - pre_verify["comments"]
        expected_revisions = expected_revision_count(summary)
        expected_comments = sum(1 for item in summary if item.get("type") == "add_comment")
        if revision_delta != expected_revisions:
            fail(
                "修订增量与计划不一致，已取消写回原文件。",
                extra={
                    "expected_revisions": expected_revisions,
                    "actual_revisions": revision_delta,
                },
            )
        if comment_delta != expected_comments:
            fail(
                "批注增量与计划不一致，已取消写回原文件。",
                extra={
                    "expected_comments": expected_comments,
                    "actual_comments": comment_delta,
                },
            )
        if verify_payload["future_timestamp_count"] > pre_verify["future_timestamp_count"]:
            fail("新增修订出现未来时间戳，已取消写回原文件。")
        if not verify_payload["zip_integrity_ok"] or not verify_payload["xml_integrity_ok"]:
            fail("修订稿结构校验失败，已取消写回原文件。")
        if not verify_payload["revision_ids_unique"]:
            fail("修订 ID 存在重复，已取消写回原文件。")
        if not verify_payload["comment_links_ok"]:
            fail("批注锚点或关系不完整，已取消写回原文件。")

        os.replace(staged_output, output)
        committed = True
    finally:
        if not committed and staged_output.exists():
            staged_output.unlink()

    verify_payload["source"] = str(output)
    revision_start_time = (
        timestamps[0].isoformat(timespec="seconds") if timestamps else None
    )
    revision_end_time = (
        timestamps[-1].isoformat(timespec="seconds") if timestamps else None
    )
    new_timestamp_samples = [
        value.isoformat(timespec="seconds") for value in timestamps
    ]
    verify_payload["new_revisions"] = revision_delta
    verify_payload["new_comments"] = comment_delta
    verify_payload["new_author"] = author
    verify_payload["new_timestamp_samples"] = new_timestamp_samples[:5]
    verify_payload["new_timezone_ok"] = all(
        value.utcoffset() == dt.timedelta(hours=8) for value in timestamps
    )
    verify_payload["new_future_timestamp_count"] = sum(
        1
        for value in timestamps
        if value > dt.datetime.now(LOCAL_TZ) + dt.timedelta(seconds=5)
    )
    return {
        "ok": True,
        "source": str(source),
        "output": str(output),
        "mode": "in_place" if in_place else "copy",
        "operation_count": len(operations),
        "word_revision_count": verify_payload["total_revisions"],
        "verify": verify_payload,
        "summary": summary,
        "author": author,
        "revision_start_time": revision_start_time,
        "revision_end_time": revision_end_time,
        "timing_mode": "automatic_contextual_real_time",
    }


def verify_docx(docx_path: Path) -> dict[str, Any]:
    ensure_docx(docx_path)
    try:
        with ZipFile(docx_path) as zf:
            bad_entry = zf.testzip()
            try:
                document_bytes = zf.read("word/document.xml")
            except KeyError:
                fail("文档缺少 word/document.xml，无法校验。")
            names = zf.namelist()
            comments_bytes = (
                zf.read("word/comments.xml")
                if "word/comments.xml" in names
                else b""
            )
            rels_bytes = (
                zf.read("word/_rels/document.xml.rels")
                if "word/_rels/document.xml.rels" in names
                else b""
            )
            content_types_bytes = (
                zf.read("[Content_Types].xml")
                if "[Content_Types].xml" in names
                else b""
            )
            core_bytes = (
                zf.read("docProps/core.xml")
                if "docProps/core.xml" in names
                else b""
            )
    except BadZipFile:
        fail("文件不是有效的 DOCX ZIP 包，无法校验。")

    try:
        document_root = ET.fromstring(document_bytes)
        comments_root = ET.fromstring(comments_bytes) if comments_bytes else None
        rels_root = ET.fromstring(rels_bytes) if rels_bytes else None
        content_types_root = (
            ET.fromstring(content_types_bytes) if content_types_bytes else None
        )
        core_root = ET.fromstring(core_bytes) if core_bytes else None
        xml_integrity_ok = True
    except ET.ParseError as exc:
        fail(f"DOCX XML 解析失败: {exc}")

    insert_nodes = document_root.findall(".//w:ins", W_NS)
    delete_nodes = document_root.findall(".//w:del", W_NS)
    revision_nodes = insert_nodes + delete_nodes
    comment_nodes = (
        comments_root.findall("w:comment", W_NS)
        if comments_root is not None
        else []
    )
    authors = sorted(
        {
            node.attrib.get(w_tag("author"), "")
            for node in revision_nodes + comment_nodes
            if node.attrib.get(w_tag("author"))
        }
    )
    timestamp_samples = [
        node.attrib[w_tag("date")]
        for node in revision_nodes + comment_nodes
        if node.attrib.get(w_tag("date"))
    ]
    parsed_timestamps: list[dt.datetime] = []
    invalid_timestamps: list[str] = []
    for sample in timestamp_samples:
        try:
            parsed = dt.datetime.fromisoformat(sample.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                invalid_timestamps.append(sample)
            else:
                parsed_timestamps.append(parsed)
        except ValueError:
            invalid_timestamps.append(sample)

    expected_offset = dt.timedelta(hours=8)
    timezone_ok = not invalid_timestamps and all(
        value.utcoffset() == expected_offset for value in parsed_timestamps
    )
    now = dt.datetime.now(LOCAL_TZ) + dt.timedelta(seconds=5)
    future_timestamps = [
        value.isoformat(timespec="seconds")
        for value in parsed_timestamps
        if value.astimezone(LOCAL_TZ) > now
    ]

    revision_ids = [
        node.attrib.get(w_tag("id"), "")
        for node in revision_nodes
        if node.attrib.get(w_tag("id")) is not None
    ]
    revision_ids_unique = len(revision_ids) == len(set(revision_ids))

    comment_ids = {
        node.attrib.get(w_tag("id"), "")
        for node in comment_nodes
        if node.attrib.get(w_tag("id")) is not None
    }
    range_start_ids = {
        node.attrib.get(w_tag("id"), "")
        for node in document_root.findall(".//w:commentRangeStart", W_NS)
    }
    range_end_ids = {
        node.attrib.get(w_tag("id"), "")
        for node in document_root.findall(".//w:commentRangeEnd", W_NS)
    }
    reference_ids = {
        node.attrib.get(w_tag("id"), "")
        for node in document_root.findall(".//w:commentReference", W_NS)
    }

    comments_relationship_ok = True
    comments_content_type_ok = True
    if comment_ids:
        rel_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
        comments_relationship_ok = bool(
            rels_root is not None
            and any(
                rel.attrib.get("Type") == rel_type
                for rel in rels_root.findall("pr:Relationship", PKG_REL_NS)
            )
        )
        comments_content_type_ok = bool(
            content_types_root is not None
            and any(
                override.attrib.get("PartName") == "/word/comments.xml"
                for override in content_types_root.findall(
                    "ct:Override",
                    CONTENT_TYPES_NS,
                )
            )
        )
    comment_links_ok = (
        comment_ids == range_start_ids == range_end_ids == reference_ids
        and comments_relationship_ok
        and comments_content_type_ok
    )

    core_author = ""
    if core_root is not None:
        core_author_element = core_root.find("cp:lastModifiedBy", CORE_NS)
        core_author = (
            core_author_element.text
            if core_author_element is not None and core_author_element.text
            else ""
        )
    return {
        "ok": True,
        "source": str(docx_path),
        "has_revisions": bool(revision_nodes),
        "insertions": len(insert_nodes),
        "deletions": len(delete_nodes),
        "comments": len(comment_nodes),
        "total_revisions": len(revision_nodes),
        "authors": authors,
        "core_author": core_author,
        "timezone_ok": timezone_ok,
        "invalid_timestamps": invalid_timestamps,
        "future_timestamp_count": len(future_timestamps),
        "future_timestamps": future_timestamps[:5],
        "timestamp_samples": timestamp_samples[:5],
        "revision_ids_unique": revision_ids_unique,
        "duplicate_revision_ids": sorted(
            {
                revision_id
                for revision_id in revision_ids
                if revision_ids.count(revision_id) > 1
            }
        ),
        "comment_links_ok": comment_links_ok,
        "zip_integrity_ok": bad_entry is None,
        "zip_bad_entry": bad_entry,
        "xml_integrity_ok": xml_integrity_ok,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DOCX 修订工具")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_parser = sub.add_parser("inspect", help="读取 docx 段落结构")
    inspect_parser.add_argument("--source", required=True, help="源 docx 路径")
    inspect_parser.add_argument("--start", type=int, default=1, help="起始段落，默认 1")
    inspect_parser.add_argument("--limit", type=int, default=80, help="返回段落数量，0 表示全部")

    apply_parser = sub.add_parser("apply", help="按 JSON 计划应用 DOCX 修订")
    apply_parser.add_argument("--plan", help="JSON 计划文件路径；不传则从 stdin 读取")

    verify_parser = sub.add_parser("verify", help="校验 docx 是否含修订标记")
    verify_parser.add_argument("--source", required=True, help="要校验的 docx 路径")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "inspect":
            payload = inspect_docx(Path(args.source), start=args.start, limit=args.limit)
        elif args.command == "apply":
            payload = apply_plan(args.plan)
        elif args.command == "verify":
            payload = verify_docx(Path(args.source))
        else:
            parser.error(f"未知命令: {args.command}")
            return
    except json.JSONDecodeError as exc:
        fail(f"JSON 计划解析失败: {exc}")
    except BadZipFile:
        fail("文件不是有效的 DOCX ZIP 包。")
    except ET.ParseError as exc:
        fail(f"DOCX XML 解析失败: {exc}")
    except OSError as exc:
        fail(f"文件操作失败: {exc}")

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
