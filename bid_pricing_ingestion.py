from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
import statistics
from typing import Any
import xml.etree.ElementTree as ET
import zipfile


@dataclass
class BoQLineItem:
    item_id: str
    description: str
    quantity: float
    unit_price: float
    line_total: float | None = None
    unit: str = ""
    bid_id: str = ""


@dataclass
class BoQLineFinding:
    code: str
    severity: str
    item_id: str
    description: str
    reason: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BoQPricingReport:
    line_count: int
    computed_subtotal: float
    stated_subtotal: float | None
    stated_grand_total: float | None
    has_anomalies: bool
    findings: list[BoQLineFinding] = field(default_factory=list)
    summary_by_severity: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_count": self.line_count,
            "computed_subtotal": self.computed_subtotal,
            "stated_subtotal": self.stated_subtotal,
            "stated_grand_total": self.stated_grand_total,
            "has_anomalies": self.has_anomalies,
            "findings": [f.to_dict() for f in self.findings],
            "summary_by_severity": dict(self.summary_by_severity),
        }


def extract_xlsx_text(file_path: str | Path) -> str:
    """Extract sheet names, rows, and tabular text from an .xlsx workbook."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"XLSX file not found: {path}")

    try:
        import openpyxl  # type: ignore
    except ImportError as exc:
        raise RuntimeError("openpyxl is required to parse .xlsx files.") from exc

    wb = openpyxl.load_workbook(path, data_only=True)
    sections: list[str] = []
    try:
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            row_lines: list[str] = [f"[Sheet: {sheet_name}]"]
            for row in ws.iter_rows(values_only=True):
                cells = [str(c).strip() for c in row if c is not None and str(c).strip() != ""]
                if cells:
                    row_lines.append(" | ".join(cells))
            if len(row_lines) > 1:
                sections.append("\n".join(row_lines))
    finally:
        wb.close()

    return "\n\n".join(sections)


def extract_pptx_text(file_path: str | Path) -> str:
    """Extract slide text and table cells from a .pptx presentation using stdlib XML parsing."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PPTX file not found: {path}")

    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    slide_sections: list[str] = []

    with zipfile.ZipFile(path, "r") as zf:
        slide_names = sorted(
            [
                name
                for name in zf.namelist()
                if re.match(r"^ppt/slides/slide\d+\.xml$", name)
            ],
            key=lambda s: int(re.search(r"slide(\d+)\.xml$", s).group(1)),  # type: ignore[union-attr]
        )

        for idx, s_name in enumerate(slide_names, start=1):
            xml_bytes = zf.read(s_name)
            root = ET.fromstring(xml_bytes)
            lines: list[str] = [f"[Slide {idx}]"]

            # Extract paragraph text blocks
            for p_elem in root.findall(".//a:p", ns):
                runs = [t.text for t in p_elem.findall(".//a:t", ns) if t.text]
                joined = "".join(runs).strip()
                if joined:
                    lines.append(joined)

            # Extract table rows if present
            for tr_elem in root.findall(".//a:tr", ns):
                cell_texts: list[str] = []
                for tc_elem in tr_elem.findall("./a:tc", ns):
                    tc_runs = [t.text for t in tc_elem.findall(".//a:t", ns) if t.text]
                    cell_str = "".join(tc_runs).strip()
                    if cell_str:
                        cell_texts.append(cell_str)
                if cell_texts:
                    lines.append(" | ".join(cell_texts))

            if len(lines) > 1:
                slide_sections.append("\n".join(lines))

    return "\n\n".join(slide_sections)


def ingest_bid_document(file_path: str | Path) -> str:
    """Route supported structured/deck files (.xlsx, .pptx, .txt, .md, .csv) to text extractors."""
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return extract_xlsx_text(path)
    if suffix == ".pptx":
        return extract_pptx_text(path)
    if suffix in {".txt", ".md", ".csv", ".json"}:
        return path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Unsupported file extension '{suffix}' for {path.name}")


def _coerce_line_item(raw: BoQLineItem | dict[str, Any], index: int) -> BoQLineItem:
    if isinstance(raw, BoQLineItem):
        return raw
    if not isinstance(raw, dict):
        raise TypeError("Expected BoQLineItem or dict for BoQ line item.")
    qty = float(raw.get("quantity", 0.0))
    unit_price = float(raw.get("unit_price", 0.0))
    line_total_raw = raw.get("line_total")
    line_total = float(line_total_raw) if line_total_raw is not None and line_total_raw != "" else None
    return BoQLineItem(
        item_id=str(raw.get("item_id") or raw.get("id") or f"LINE-{index + 1}").strip(),
        description=str(raw.get("description") or raw.get("item") or "").strip(),
        quantity=qty,
        unit_price=unit_price,
        line_total=line_total,
        unit=str(raw.get("unit") or "").strip(),
        bid_id=str(raw.get("bid_id") or "").strip(),
    )


def evaluate_boq_pricing(
    items: list[BoQLineItem | dict[str, Any]],
    stated_subtotal: float | None = None,
    stated_grand_total: float | None = None,
    vat_rate: float = 0.0,
    tolerance: float = 0.01,
    peer_unit_prices_by_item: dict[str, list[float]] | None = None,
    outlier_multiplier: float = 2.0,
) -> BoQPricingReport:
    """Validate BoQ line math (qty * unit_price), totals, and peer unit-price outliers."""
    coerced = [_coerce_line_item(item, i) for i, item in enumerate(items or [])]
    findings: list[BoQLineFinding] = []
    computed_subtotal = 0.0
    tol = max(0.0, float(tolerance))
    mult = max(1.0, float(outlier_multiplier))
    peer_map = peer_unit_prices_by_item or {}

    for line in coerced:
        if line.quantity < 0 or line.unit_price < 0:
            findings.append(
                BoQLineFinding(
                    code="NEGATIVE_PRICING_VALUE",
                    severity="HIGH",
                    item_id=line.item_id,
                    description=line.description,
                    reason="Negative quantity or unit price detected on BoQ line item.",
                    details={"quantity": line.quantity, "unit_price": line.unit_price},
                )
            )

        expected_total = round(line.quantity * line.unit_price, 4)
        effective_total = expected_total

        if line.line_total is not None:
            diff = abs(float(line.line_total) - expected_total)
            if diff > tol:
                findings.append(
                    BoQLineFinding(
                        code="LINE_MATH_MISMATCH",
                        severity="HIGH",
                        item_id=line.item_id,
                        description=line.description,
                        reason=f"Line total ({line.line_total:.2f}) differs from quantity * unit_price ({expected_total:.2f}) by {diff:.2f}.",
                        details={
                            "quantity": line.quantity,
                            "unit_price": line.unit_price,
                            "expected_total": expected_total,
                            "stated_line_total": float(line.line_total),
                            "difference": round(diff, 4),
                        },
                    )
                )
            effective_total = float(line.line_total)

        computed_subtotal = round(computed_subtotal + effective_total, 4)

        # Peer unit-price outlier check against median when peers are provided
        peers = [float(p) for p in peer_map.get(line.item_id, []) if p is not None and float(p) > 0]
        if len(peers) >= 2 and line.unit_price > 0:
            med = float(statistics.median(peers))
            if med > 0 and (line.unit_price >= med * mult or line.unit_price <= med / mult):
                ratio = round(line.unit_price / med, 2)
                findings.append(
                    BoQLineFinding(
                        code="UNIT_PRICE_OUTLIER",
                        severity="MEDIUM",
                        item_id=line.item_id,
                        description=line.description,
                        reason=f"Unit price ({line.unit_price:.2f}) deviates significantly from peer median ({med:.2f}; {ratio}x).",
                        details={
                            "unit_price": line.unit_price,
                            "peer_median": med,
                            "ratio_to_median": ratio,
                            "peer_count": len(peers),
                        },
                    )
                )

    if stated_subtotal is not None:
        sub_val = float(stated_subtotal)
        sub_diff = abs(sub_val - computed_subtotal)
        if sub_diff > tol:
            findings.append(
                BoQLineFinding(
                    code="SUBTOTAL_MISMATCH",
                    severity="HIGH",
                    item_id="SUBTOTAL",
                    description="BoQ Subtotal",
                    reason=f"Stated subtotal ({sub_val:.2f}) differs from summed lines ({computed_subtotal:.2f}) by {sub_diff:.2f}.",
                    details={
                        "stated_subtotal": sub_val,
                        "computed_subtotal": computed_subtotal,
                        "difference": round(sub_diff, 4),
                    },
                )
            )

    if stated_grand_total is not None:
        grand_val = float(stated_grand_total)
        base_for_grand = float(stated_subtotal) if stated_subtotal is not None else computed_subtotal
        expected_grand = round(base_for_grand * (1.0 + max(0.0, float(vat_rate))), 4)
        grand_diff = abs(grand_val - expected_grand)
        if grand_diff > tol:
            findings.append(
                BoQLineFinding(
                    code="GRAND_TOTAL_MISMATCH",
                    severity="HIGH",
                    item_id="GRAND_TOTAL",
                    description="BoQ Grand Total",
                    reason=f"Stated grand total ({grand_val:.2f}) differs from expected total ({expected_grand:.2f}) by {grand_diff:.2f}.",
                    details={
                        "stated_grand_total": grand_val,
                        "expected_grand_total": expected_grand,
                        "vat_rate": float(vat_rate),
                        "difference": round(grand_diff, 4),
                    },
                )
            )

    summary_by_severity: dict[str, int] = {}
    for f in findings:
        summary_by_severity[f.severity] = summary_by_severity.get(f.severity, 0) + 1

    return BoQPricingReport(
        line_count=len(coerced),
        computed_subtotal=computed_subtotal,
        stated_subtotal=float(stated_subtotal) if stated_subtotal is not None else None,
        stated_grand_total=float(stated_grand_total) if stated_grand_total is not None else None,
        has_anomalies=bool(findings),
        findings=findings,
        summary_by_severity=summary_by_severity,
    )