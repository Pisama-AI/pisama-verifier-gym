"""Compute agreement for the packaged WildChat derailment verifier export."""

from pisama_verifier_gym import agreement_table, load_builtin_verdicts

rows = load_builtin_verdicts()
for stat in agreement_table(rows):
    print(
        stat.vendor_a,
        stat.vendor_b,
        f"n={stat.usable_n}",
        f"raw={stat.raw_agreement:.2f}",
        f"psa={stat.positive_specific_agreement:.2f}"
        if stat.positive_specific_agreement is not None
        else "psa=n/a",
        f"kappa={stat.cohen_kappa:.2f}",
    )
