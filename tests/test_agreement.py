from pytest import approx

from pisama_verifier_gym import (
    agreement_table,
    load_builtin_verdicts,
    pairwise_agreement,
    vendor_names,
    verdict_balance,
)


def test_builtin_agreement_matches_datasheet():
    rows = load_builtin_verdicts()

    assert len(rows) == 97
    assert vendor_names(rows) == [
        "claude-sonnet-4-6",
        "gemini-2.5-flash-lite",
        "gpt-5.5",
    ]

    stats = {
        (stat.vendor_a, stat.vendor_b): stat
        for stat in agreement_table(rows)
    }

    anthropic_google = stats[("claude-sonnet-4-6", "gemini-2.5-flash-lite")]
    assert_pair(anthropic_google, usable_n=91, raw=0.96, psa=0.0, kappa=-0.02)

    anthropic_openai = stats[("claude-sonnet-4-6", "gpt-5.5")]
    assert_pair(anthropic_openai, usable_n=91, raw=0.98, psa=0.0, kappa=0.0)

    google_openai = stats[("gemini-2.5-flash-lite", "gpt-5.5")]
    assert_pair(google_openai, usable_n=95, raw=0.96, psa=0.0, kappa=-0.02)


def test_verdict_balance_counts_yes_no_and_abstain():
    rows = load_builtin_verdicts()
    balance = verdict_balance(rows)

    assert balance["claude-sonnet-4-6"].yes == 2
    assert balance["claude-sonnet-4-6"].abstain == 6
    assert balance["claude-sonnet-4-6"].no == 89

    assert balance["gemini-2.5-flash-lite"].yes == 2
    assert balance["gemini-2.5-flash-lite"].abstain == 0
    assert balance["gemini-2.5-flash-lite"].no == 95

    assert balance["gpt-5.5"].yes == 2
    assert balance["gpt-5.5"].abstain == 2
    assert balance["gpt-5.5"].no == 93


def test_pairwise_agreement_drops_abstentions_per_pair():
    rows = [
        {"per_vendor_verdicts": {"a": {"verdict": True}, "b": {"verdict": True}}},
        {"per_vendor_verdicts": {"a": {"verdict": True}, "b": {"verdict": False}}},
        {"per_vendor_verdicts": {"a": {"verdict": None}, "b": {"verdict": False}}},
        {"per_vendor_verdicts": {"a": {"verdict": False}, "b": {"verdict": False}}},
    ]

    stats = pairwise_agreement(rows, "a", "b")

    assert stats is not None
    assert stats.usable_n == 3
    assert stats.true_true == 1
    assert stats.true_false == 1
    assert stats.false_true == 0
    assert stats.false_false == 1
    assert stats.raw_agreement == approx(2 / 3)
    assert stats.positive_specific_agreement == approx(2 / 3)


def assert_pair(stats, *, usable_n, raw, psa, kappa):
    assert stats.usable_n == usable_n
    assert stats.raw_agreement == approx(raw, abs=0.005)
    assert stats.positive_specific_agreement == psa
    assert stats.cohen_kappa == approx(kappa, abs=0.005)
