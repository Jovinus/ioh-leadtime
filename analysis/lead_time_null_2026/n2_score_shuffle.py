"""N2 — does alert timing carry case-specific information, or is it the scoring policy?

This is the analysis that decides how the finding is stated.

Within a cell, whole score sequences are permuted across cases.  Each recipient keeps its
own window length, its own reference time and its own denominator; only the sequence it is
scored with comes from somebody else.  The crossing, the lead and the ratio are then
recomputed against the **unchanged** transported threshold.

What the permutation preserves is the score's *generic* temporal profile -- the rise off the
first scored minute onto the plateau, and the plateau's height.  What it destroys is any
correspondence between a sequence and the patient it came from.  So:

* If the shuffled ratio sits at the observed ratio, alert timing carries no case-specific
  information, and the reported lead is a property of the scoring policy interacting with
  the observation window.  That is the paper's claim stated as a null result, which is much
  harder to dismiss than a correlation.
* If the shuffled ratio sits materially below the observed ratio, part of the timing is
  case-specific and **the claim must be weakened**.

Both outcomes are reported at full strength.  The rule below was fixed before the numbers
were looked at, because choosing an alignment after seeing the answer would invalidate the
null.

## The alignment rule, and the two variants

Donor sequences are laid onto recipients by **elapsed minutes from the start of the
recipient's own alert window**, never by ``t_to_event``.  Aligning by ``t_to_event`` would
carry the donor's distance-to-onset structure across and destroy exactly the generic
start-of-sequence profile the null is supposed to keep.

Length mismatch is handled two ways, and both are reported, because neither is obviously
right and they bias in the same direction by different amounts:

* ``hold`` (**primary**) -- the donor is drawn uniformly from every case in the cell and its
  last observed value is held forward over any recipient minutes it does not reach.  Uses
  the whole donor pool and selects on nothing.  Holding a plateau value forward can only
  sustain a crossing that the donor's own trajectory had already reached, so it does not
  invent early crossings.
* ``longer`` (**sensitivity**) -- the donor is drawn only from cases whose window is at
  least as long as the recipient's, so no filling is needed.  This selects donors on length:
  a long donor's window starts mid-case, where the score is already on the plateau, so short
  recipients receive plateaued sequences that cross at once.  That biases the null ratio
  **up**, toward 1.

Both variants therefore bias the null upward rather than downward, which is the direction
that makes "shuffled is close to observed" *easier* to obtain.  That is the direction which
favours the paper's headline, so it is stated here rather than buried: a null that agrees
with the observed value is weaker evidence than it looks, and the report says so.  What the
two variants together do establish is a bracket -- if the observed ratio sits *above* both
nulls, the upward bias cannot explain it.

Permutations are derangements: no case is ever scored with its own sequence.

Post-hoc on cached scores.  Nothing is retrained, refitted or re-scored, and the threshold
is never re-derived.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib_n import (  # noqa: E402
    ALERT_WINDOW_MIN,
    COHORT_LABELS,
    FAMILY_LABELS,
    N_PERMUTATIONS,
    cells,
    df_to_md,
    first_crossing_elapsed,
    headline_cuts,
    per_case_leads,
    percentile_ci,
    seed_for,
    weighted_spearman,
    window_matrix,
    write_manifest,
)

OUT = Path(__file__).resolve().parent / "n2_score_shuffle"

VARIANTS = ("hold", "longer")


def _hold_forward(scores: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Each row's last observed value carried forward over its unobserved tail.

    Rows are dense from elapsed 0 up to their own length, so a single forward fill along the
    elapsed axis is enough; there are no interior gaps to bridge.
    """
    filled = scores.copy()
    n_rows, n_cols = filled.shape
    for column in range(1, n_cols):
        missing = ~valid[:, column]
        filled[missing, column] = filled[missing, column - 1]
    return filled


def _derangement(n: int, rng: np.random.Generator) -> np.ndarray:
    """A permutation with no fixed point.  Resample-and-repair, which is O(n) in practice."""
    perm = rng.permutation(n)
    fixed = np.flatnonzero(perm == np.arange(n))
    while fixed.size:
        if fixed.size == 1:
            # Swap the single fixed point with a random other position.
            other = int(rng.integers(0, n))
            while other == fixed[0]:
                other = int(rng.integers(0, n))
            index = int(fixed[0])
            perm[index], perm[other] = perm[other], perm[index]
        else:
            perm[fixed] = perm[rng.permutation(fixed)]
        fixed = np.flatnonzero(perm == np.arange(n))
    return perm


def _longer_donor(lengths: np.ndarray, order: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """For each case, a donor index drawn uniformly among cases at least as long.

    ``order`` sorts cases by ascending length, so the eligible set for the case at sorted
    position ``k`` is the suffix ``order[k:]``.  Drawing a uniform position in that suffix is
    one integer draw per case.  A case whose length is the maximum has only itself eligible;
    that single unavoidable fixed point is repaired by swapping with the previous position.
    """
    n = lengths.size
    donor = np.empty(n, dtype=np.int64)
    rank = np.empty(n, dtype=np.int64)
    rank[order] = np.arange(n)
    picks = rng.integers(rank, n)  # uniform in [rank_i, n)
    donor = order[picks]
    self_picked = np.flatnonzero(donor == np.arange(n))
    for index in self_picked:
        position = int(rank[index])
        if position + 1 < n:
            alternative = int(rng.integers(position + 1, n))
            donor[index] = order[alternative]
        elif position > 0:
            donor[index] = order[position - 1]
    return donor


def _cell(family: str, cohort: str, cut: float) -> list[dict]:
    observed_frame = per_case_leads(family, cohort, cut)
    observed_ratio = float(np.median(observed_frame["ratio"].to_numpy(float)))
    observed_rho = float(
        weighted_spearman(
            observed_frame["observed_min"].to_numpy(float),
            observed_frame["lead"].to_numpy(float),
            np.ones(len(observed_frame), int),
        )
    )
    observed_lead = float(np.median(observed_frame["lead"].to_numpy(float)))

    scores, valid, cases = window_matrix(family, cohort)
    filled = _hold_forward(scores, valid)
    is_event = (cases["label"] == 1).to_numpy()
    observed_min = cases["observed_min"].to_numpy(float)
    lengths = cases["n_window_minutes"].to_numpy(np.int64)
    order = np.argsort(lengths, kind="mergesort")
    n_cases = len(cases)

    rows: list[dict] = []
    for variant in VARIANTS:
        rng = np.random.default_rng(seed_for("n2", family, cohort) + VARIANTS.index(variant))
        null_ratio = np.full(N_PERMUTATIONS, np.nan)
        null_rho = np.full(N_PERMUTATIONS, np.nan)
        null_lead = np.full(N_PERMUTATIONS, np.nan)
        null_detected = np.zeros(N_PERMUTATIONS)

        for draw in range(N_PERMUTATIONS):
            if variant == "hold":
                donor = _derangement(n_cases, rng)
                donor_scores = filled[donor]
                # The recipient's own window length is what limits where a crossing can be
                # found; the donor supplies only the values.
                mask = valid
            else:
                donor = _longer_donor(lengths, order, rng)
                donor_scores = scores[donor]
                mask = valid & np.isfinite(donor_scores)

            first = first_crossing_elapsed(donor_scores, mask, cut)
            crossed = (first >= 0) & is_event & (observed_min > 0)
            if crossed.sum() < 3:
                continue
            lead = observed_min[crossed] - first[crossed]
            window = observed_min[crossed]
            null_detected[draw] = int(crossed.sum())
            null_lead[draw] = float(np.median(lead))
            null_ratio[draw] = float(np.median(lead / window))
            null_rho[draw] = weighted_spearman(window, lead, np.ones(crossed.sum(), int))

        def _p(draws: np.ndarray, observed: float) -> float:
            finite = draws[np.isfinite(draws)]
            if finite.size == 0:
                return float("nan")
            below = float((finite >= observed).mean())
            above = float((finite <= observed).mean())
            return float(min(1.0, max(2.0 * min(below, above), 2.0 / finite.size)))

        row = {
            "family": family,
            "family_label": FAMILY_LABELS[family],
            "cohort": cohort,
            "cohort_label": COHORT_LABELS[cohort],
            "variant": variant,
            "n_cases": int(n_cases),
            "n_event_cases": int(is_event.sum()),
            "n_detected_observed": int(len(observed_frame)),
            "n_detected_null_mean": float(np.nanmean(null_detected)),
            "observed_ratio_median": observed_ratio,
            "observed_lead_median": observed_lead,
            "observed_spearman": observed_rho,
            "null_ratio_mean": float(np.nanmean(null_ratio)),
            "null_lead_mean": float(np.nanmean(null_lead)),
            "null_spearman_mean": float(np.nanmean(null_rho)),
            "excess_ratio": observed_ratio - float(np.nanmean(null_ratio)),
            "excess_spearman": observed_rho - float(np.nanmean(null_rho)),
            "p_ratio": _p(null_ratio, observed_ratio),
            "p_spearman": _p(null_rho, observed_rho),
            "n_permutations": N_PERMUTATIONS,
        }
        row["null_ratio_ci_lo"], row["null_ratio_ci_hi"] = percentile_ci(null_ratio)
        row["null_lead_ci_lo"], row["null_lead_ci_hi"] = percentile_ci(null_lead)
        row["null_spearman_ci_lo"], row["null_spearman_ci_hi"] = percentile_ci(null_rho)
        rows.append(row)
    return rows


def run() -> pd.DataFrame:
    OUT.mkdir(parents=True, exist_ok=True)
    cuts = headline_cuts()
    rows: list[dict] = []
    for family, cohort in cells():
        rows.extend(_cell(family, cohort, float(cuts[family])))
        print(f"  {family}/{cohort} done", flush=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(OUT / "n2_score_shuffle.csv", index=False)
    return frame


def _variant_table(frame: pd.DataFrame, variant: str) -> pd.DataFrame:
    part = frame[frame["variant"] == variant]
    return pd.DataFrame(
        {
            "Model": part["family_label"],
            "Cohort": part["cohort_label"],
            "Observed ratio": part["observed_ratio_median"].map("{:.3f}".format),
            "Shuffled ratio (95% CI)": [
                f"{r.null_ratio_mean:.3f} ({r.null_ratio_ci_lo:.3f}–{r.null_ratio_ci_hi:.3f})"
                for r in part.itertuples()
            ],
            "Excess": part["excess_ratio"].map("{:+.3f}".format),
            "p": part["p_ratio"].map("{:.3g}".format),
            "Observed ρ": part["observed_spearman"].map("{:.3f}".format),
            "Shuffled ρ (95% CI)": [
                f"{r.null_spearman_mean:.3f} "
                f"({r.null_spearman_ci_lo:.3f}–{r.null_spearman_ci_hi:.3f})"
                for r in part.itertuples()
            ],
            "Excess ρ": part["excess_spearman"].map("{:+.3f}".format),
            "p (ρ)": part["p_spearman"].map("{:.3g}".format),
        }
    )


def _write_report(frame: pd.DataFrame) -> None:
    primary = frame[frame["variant"] == "hold"]
    lo, hi = primary["excess_ratio"].min(), primary["excess_ratio"].max()
    rho_lo, rho_hi = primary["excess_spearman"].min(), primary["excess_spearman"].max()
    n_above = int((primary["excess_ratio"] > 0).sum())
    n_sig = int((primary["p_ratio"] < 0.05).sum())

    lines = [
        "# N2 — cross-case score-sequence shuffle null",
        "",
        "Whole score sequences are permuted across cases inside a cell. Each recipient keeps "
        "its own window length, reference time and denominator; only the sequence it is "
        "scored with comes from somebody else. The crossing is recomputed against the "
        "unchanged transported threshold.",
        "",
        "The permutation keeps the score's generic temporal profile, including the plateau, "
        "and destroys any correspondence between a sequence and the patient it came from.",
        "",
        "## Headline",
        "",
        f"On the primary `hold` variant, the observed median ratio exceeds the shuffled null "
        f"in **{n_above} of 15** cells, by **{lo:+.3f} to {hi:+.3f}**, with "
        f"**{n_sig} of 15** at p < 0.05. Excess Spearman ranges "
        f"**{rho_lo:+.3f} to {rho_hi:+.3f}**.",
        "",
        "## Primary variant — `hold`",
        "",
        "Donor drawn uniformly from every case in the cell; its last observed value held "
        "forward over any recipient minutes it does not reach.",
        "",
        df_to_md(_variant_table(frame, "hold")),
        "",
        "## Sensitivity variant — `longer`",
        "",
        "Donor drawn only from cases whose window is at least as long as the recipient's, so "
        "no filling is needed. Selects donors on length, which biases the null ratio up.",
        "",
        df_to_md(_variant_table(frame, "longer")),
        "",
        "## How to read this, and what it cannot show",
        "",
        "Both variants bias the null **upward**, by different amounts and for different "
        "reasons -- `longer` because a long donor's window starts mid-case where the score "
        "is already on the plateau, `hold` because a held plateau value sustains a crossing "
        "across the recipient's tail. Upward bias is the direction that makes "
        "\"shuffled is close to observed\" easier to obtain, which is the direction that "
        "favours reading the ratio as a property of the scoring policy. A null that agrees "
        "with the observed value is therefore weaker evidence than it appears, and that is "
        "stated rather than left for a reader to notice.",
        "",
        "What the two variants together do establish is a bracket. Where the observed ratio "
        "sits **above** both nulls, the upward bias cannot account for it, and the timing "
        "carries information the shuffle destroyed.",
        "",
        "## Method",
        "",
        "Donor sequences are laid onto recipients by elapsed minutes from the start of the "
        "recipient's own alert window, never by `t_to_event`: aligning by `t_to_event` would "
        "carry the donor's distance-to-onset structure across and destroy the generic "
        "start-of-sequence profile the null exists to preserve. Permutations are "
        "derangements, so no case is ever scored with its own sequence. "
        f"{N_PERMUTATIONS:,} permutations per cell per variant. The alert window is "
        f"`0 < t_to_event <= {ALERT_WINDOW_MIN}` and the threshold is the transported "
        "80%-target raw-score cut, neither re-derived nor reselected. `p` is two-sided by "
        f"interval inversion on the null draws, floored at 2/{N_PERMUTATIONS:,}.",
        "",
    ]
    (OUT / "n2_score_shuffle.md").write_text("\n".join(lines))


def main() -> None:
    frame = run()
    _write_report(frame)
    write_manifest(
        OUT,
        "n2_score_shuffle",
        [],
        extra={
            "n_cells": int(frame["family"].nunique() * frame["cohort"].nunique()),
            "variants": list(VARIANTS),
            "n_permutations": N_PERMUTATIONS,
        },
        hash_inputs=False,
    )
    primary = frame[frame["variant"] == "hold"]
    print(
        f"N2: excess ratio over shuffle null (hold) "
        f"{primary['excess_ratio'].min():+.3f} to {primary['excess_ratio'].max():+.3f}; "
        f"{int((primary['excess_ratio'] > 0).sum())}/15 cells above null"
    )


if __name__ == "__main__":
    main()
