import json

import pytest

from pisama_verifier_gym import (
    agreement_table,
    load_verdict_rows,
    pairwise_agreement,
    vendor_names,
    verdict_balance,
)


def write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_load_verdict_rows_accepts_blank_lines_and_valid_null_verdicts(tmp_path):
    path = tmp_path / "verdicts.jsonl"
    path.write_text(
        '\n{"per_vendor_verdicts":{"a":{"verdict":true},"b":{"verdict":null}}}\n\n',
        encoding="utf-8",
    )

    rows = load_verdict_rows(path)

    assert len(rows) == 1
    assert verdict_balance(rows)["b"].abstain == 1


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ('{"per_vendor_verdicts":\n', "invalid JSON on line 1"),
        ("[]\n", "line 1 is not a JSON object"),
        ('{"source_trace_id":"row-1"}\n', "has no per_vendor_verdicts object"),
        ('{"per_vendor_verdicts":{"":{"verdict":true}}}\n', "invalid vendor name"),
        ('{"per_vendor_verdicts":{"a":{}}}\n', "has no verdict for vendor 'a'"),
        (
            '{"per_vendor_verdicts":{"a":{"verdict":"yes"}}}\n',
            "non-boolean verdict for vendor 'a'",
        ),
    ],
)
def test_load_verdict_rows_rejects_malformed_contracts(tmp_path, contents, message):
    path = tmp_path / "invalid.jsonl"
    path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_verdict_rows(path)


def test_pairwise_agreement_returns_none_without_a_definite_pair():
    rows = [{"per_vendor_verdicts": {"a": {"verdict": None}, "b": {"verdict": True}}}]

    assert pairwise_agreement(rows, "a", "b") is None
    assert agreement_table(rows) == []


def test_pairwise_agreement_handles_an_all_negative_panel():
    rows = [{"per_vendor_verdicts": {"a": {"verdict": False}, "b": {"verdict": False}}}]

    stats = pairwise_agreement(rows, "a", "b")

    assert stats is not None
    assert stats.positive_specific_agreement is None
    assert stats.cohen_kappa == 0.0
    assert stats.as_dict()["false_false"] == 1


def test_programmatic_rows_treat_invalid_vendor_payloads_as_abstentions():
    rows = [
        {},
        {
            "per_vendor_verdicts": {
                "a": "invalid",
                "b": {"verdict": "not-a-boolean"},
            }
        },
    ]

    assert vendor_names(rows) == ["a", "b"]
    balance = verdict_balance(rows)
    assert balance["a"].as_dict()["abstain"] == 2
    assert balance["b"].abstain == 2
