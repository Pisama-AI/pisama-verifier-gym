"""Agreement metrics for verifier panel verdict exports."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence

VerdictRow = Mapping[str, Any]


@dataclass(frozen=True)
class AgreementStats:
    """Pairwise agreement for two verifier panel members."""

    vendor_a: str
    vendor_b: str
    usable_n: int
    raw_agreement: float
    positive_specific_agreement: float | None
    cohen_kappa: float
    true_true: int
    true_false: int
    false_true: int
    false_false: int

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


@dataclass(frozen=True)
class VerdictBalance:
    """Yes, no, and abstention counts for one panel member."""

    vendor: str
    yes: int
    no: int
    abstain: int
    total: int

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


def load_verdict_rows(path: str | Path) -> list[dict[str, Any]]:
    """Load a JSONL verdict export.

    Each row must contain a ``per_vendor_verdicts`` mapping whose values include
    a ``verdict`` key set to ``true``, ``false``, or ``null``.
    """
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                msg = f"invalid JSON on line {line_number}: {exc.msg}"
                raise ValueError(msg) from exc
            if not isinstance(row, dict):
                raise ValueError(f"line {line_number} is not a JSON object")
            rows.append(row)
    return rows


def vendor_names(rows: Sequence[VerdictRow]) -> list[str]:
    """Return sorted verifier names found in a verdict export."""
    names: set[str] = set()
    for row in rows:
        verdicts = _vendor_verdicts(row)
        names.update(str(name) for name in verdicts)
    return sorted(names)


def pairwise_agreement(
    rows: Sequence[VerdictRow],
    vendor_a: str,
    vendor_b: str,
) -> AgreementStats | None:
    """Compute pairwise agreement for two vendors.

    Rows where either vendor abstained are dropped for this pair only.
    """
    counts = _pair_counts(rows, vendor_a, vendor_b)
    true_true = counts[(True, True)]
    true_false = counts[(True, False)]
    false_true = counts[(False, True)]
    false_false = counts[(False, False)]

    usable_n = true_true + true_false + false_true + false_false
    if usable_n == 0:
        return None

    raw = (true_true + false_false) / usable_n
    psa_denominator = (2 * true_true) + true_false + false_true
    psa = (2 * true_true / psa_denominator) if psa_denominator else None

    p_yes_a = (true_true + true_false) / usable_n
    p_yes_b = (true_true + false_true) / usable_n
    expected = (p_yes_a * p_yes_b) + ((1 - p_yes_a) * (1 - p_yes_b))
    kappa = (raw - expected) / (1 - expected) if expected < 1 else 0.0

    return AgreementStats(
        vendor_a=vendor_a,
        vendor_b=vendor_b,
        usable_n=usable_n,
        raw_agreement=raw,
        positive_specific_agreement=psa,
        cohen_kappa=kappa,
        true_true=true_true,
        true_false=true_false,
        false_true=false_true,
        false_false=false_false,
    )


def agreement_table(rows: Sequence[VerdictRow]) -> list[AgreementStats]:
    """Compute agreement for every vendor pair in sorted order."""
    stats: list[AgreementStats] = []
    for vendor_a, vendor_b in combinations(vendor_names(rows), 2):
        pair = pairwise_agreement(rows, vendor_a, vendor_b)
        if pair is not None:
            stats.append(pair)
    return stats


def verdict_balance(rows: Sequence[VerdictRow]) -> dict[str, VerdictBalance]:
    """Count yes, no, and abstention verdicts for each vendor."""
    balance = {
        vendor: {"yes": 0, "no": 0, "abstain": 0}
        for vendor in vendor_names(rows)
    }

    for row in rows:
        for vendor in balance:
            value = _verdict_for_vendor(row, vendor)
            if value is True:
                balance[vendor]["yes"] += 1
            elif value is False:
                balance[vendor]["no"] += 1
            else:
                balance[vendor]["abstain"] += 1

    return {
        vendor: VerdictBalance(
            vendor=vendor,
            yes=counts["yes"],
            no=counts["no"],
            abstain=counts["abstain"],
            total=len(rows),
        )
        for vendor, counts in balance.items()
    }


def _vendor_verdicts(row: VerdictRow) -> Mapping[str, Any]:
    value = row.get("per_vendor_verdicts")
    if not isinstance(value, Mapping):
        return {}
    return value


def _pair_counts(
    rows: Sequence[VerdictRow],
    vendor_a: str,
    vendor_b: str,
) -> dict[tuple[bool, bool], int]:
    counts = {
        (True, True): 0,
        (True, False): 0,
        (False, True): 0,
        (False, False): 0,
    }
    for row in rows:
        pair = _definite_pair(row, vendor_a, vendor_b)
        if pair is not None:
            counts[pair] += 1
    return counts


def _definite_pair(
    row: VerdictRow,
    vendor_a: str,
    vendor_b: str,
) -> tuple[bool, bool] | None:
    value_a = _verdict_for_vendor(row, vendor_a)
    value_b = _verdict_for_vendor(row, vendor_b)
    if value_a is None or value_b is None:
        return None
    return value_a, value_b


def _verdict_for_vendor(row: VerdictRow, vendor: str) -> bool | None:
    verdicts = _vendor_verdicts(row)
    vendor_payload = verdicts.get(vendor)
    if not isinstance(vendor_payload, Mapping):
        return None
    verdict = vendor_payload.get("verdict")
    return verdict if isinstance(verdict, bool) else None
