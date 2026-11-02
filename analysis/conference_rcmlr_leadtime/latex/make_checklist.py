"""Fill the official NeurIPS 2026 checklist template with this paper's answers.

The template is taken verbatim from the venue's Formatting_Instructions zip and the
instruction block is stripped, as the template itself directs. Nothing else in it is
edited: the section heading, the sixteen questions and their guideline blocks stay
exactly as shipped, and only \\answerTODO / \\justificationTODO are substituted, in
order. Regenerating from the template rather than hand-copying it is what keeps the
questions from drifting.

Run:
    conda run -n torch python make_checklist.py
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TEMPLATE = (
    REPO
    / "neurips_workshop"
    / "checklist_guidelines"
    / "Formatting_Instructions_For_NeurIPS_2026"
    / "checklist.tex"
)
OUT = HERE / "checklist.tex"

# (answer macro, justification) in the template's own order.
ANSWERS: list[tuple[str, str]] = [
    # 1 Claims
    (
        r"\answerYes{}",
        "The abstract and Section 1 state the four contributions and their scope, and both "
        "say the paper measures neither clinician comprehension nor physiology. Section 3 "
        "and Section 7 distinguish the observed lead--window association from what the "
        "upward-biased references can establish, and Section 4 treats the cross-family "
        "score-path property as descriptive rather than causal.",
    ),
    # 2 Limitations
    (
        r"\answerYes{}",
        "Section 7 is a separate limitations section covering the retrospective design, the "
        "single outcome definition, single training seed and operating-point family, the "
        "the shared hospital of two cohorts, a weak headline exemplar, reference upward "
        "bias, the single clinical domain, the non-systematic literature sample, and the unvalidated communication and reporting proposals.",
    ),
    # 3 Theory
    (
        r"\answerNA{}",
        "The paper contains no theorems, lemmas or formal results. Its claims are empirical "
        "and each is measured on cached scores.",
    ),
    # 4 Reproducibility
    (
        r"\answerYes{}",
        "Yes. Two standards should be distinguished. Independent reimplementation is "
        "supported: Section 2 gives the task, cohorts, scoring policy and alert rule; "
        "Appendix A.1 gives the split sizes and seed, the eligibility rules, the twenty "
        "inputs and how each family consumes them, every architecture and training "
        "hyperparameter, and the software versions; Appendix A.19 records the seeds and "
        "resampling counts; both datasets are available under their providers' access "
        "procedures; and the analysis code is released at the repository "
        "Appendix A.1 names. Bit-for-bit reproduction from raw data is not supported here, "
        "because the repository carries no patient-level or derived patient-level files: the "
        "cached per-minute scores the analyses read are derived patient-level data and are not "
        "redistributed there, so a reader must obtain the data from its provider. We "
        "claim the first and not the second.",
    ),
    # 5 Open access to data and code
    (
        r"\answerYes{}",
        "The analysis code is released at https://github.com/Jovinus/ioh-leadtime, archived "
        "at DOI 10.5281/zenodo.23881391, under the Apache License 2.0, together with the aggregate result files behind every "
        "table and figure, so "
        "the table and figure checks run from the repository as shipped. Neither dataset is "
        "redistributed there, and neither are the cached per-minute scores, which are derived "
        "patient-level data. Each is obtained from its own provider: VitalDB v1.0.0 is openly "
        "accessible from PhysioNet under the Creative Commons Attribution-NonCommercial-"
        "ShareAlike 4.0 International (CC BY-NC-SA 4.0) license, and MOVER is available from the UCI Machine Learning Repository "
        "to researchers who sign its data use agreement, as Appendix A.1 records. Appendix A.1 "
        "specifies the construction to the level a reimplementation needs.",
    ),
    # 6 Experimental setting/details
    (
        r"\answerYes{}",
        "Appendix A.1 gives the subject-aware split and its sizes, the seed, the per-minute "
        "eligibility rules, the feature set, and for each of the five families the "
        "architecture, optimizer, learning rate, weight decay, batch size, epoch budget and "
        "early-stopping rule. Section 2 gives the calibration and threshold policy: fitted "
        "on the development validation split at an 80\\% case-level sensitivity target and "
        "transported unchanged, with nothing reselected.",
    ),
    # 7 Statistical significance
    (
        r"\answerYes{}",
        "Every interval in the paper is a 95\\% cluster bootstrap on the clustering unit "
        "named in Section 2, the subject for two cohorts and the case for MOVER (SIS), at "
        "2,000 replicates. The two references of Section 3 use 1,000 permutations per "
        "cell, and are reported as the 2.5th and 97.5th percentiles of the reference "
        "distribution rather than as symmetric error bars. The cross-combination rank "
        "correlations of Section 4 are reported as point estimates with no accompanying "
        "test, because the fifteen combinations are not independent replications; "
        "Appendix A.19 records why. Every "
        "interval is pointwise and descriptive, and no family-wise coverage is claimed "
        "across the fifteen cells. Appendix A.18 records the multiplicity family and its "
        "Benjamini--Hochberg adjustment, and Appendix A.19 the seeds and every "
        "resampling count.",
    ),
    # 8 Compute
    (
        r"\answerYes{}",
        "Appendix A.1 reports the hardware (one Apple M3 Ultra desktop with 512 GB unified "
        "memory, PyTorch on the Metal backend, no GPU cluster), the wall clock for each of "
        "the five models, and the fact that the project trained more than the paper reports, "
        "namely a seven-point lead-time sweep per family. The analyses in this paper add no "
        "training and read cached scores.",
    ),
    # 9 Code of ethics
    (
        r"\answerYes{}",
        "The research conforms to the NeurIPS Code of Ethics. It is a secondary analysis of "
        "de-identified data obtained under their respective provider access and license "
        "terms, with an institutional review board exemption and consent waiver (EUMC "
        "2026-08-011) recorded in Appendix A.1, and it proposes no model for clinical use.",
    ),
    # 10 Broader impacts
    (
        r"\answerYes{}",
        "The paper's subject is a negative societal impact of current practice: a reported "
        "median alert lead time invites a warning-time interpretation while remaining "
        "strongly coupled to observation length, which can overstate what a deployed monitor offers. "
        "Section 5 shows that two natural repairs fail, including one whose sensitivity cost "
        "is quantified, and Section 6.3 proposes four reporting items as the mitigation. "
        "Section 7 is explicit that this is retrospective assessment and not deployment "
        "clearance.",
    ),
    # 11 Safeguards
    (
        r"\answerNA{}",
        "No model, checkpoint or dataset is released, and the paper proposes no model for "
        "clinical use, so there is nothing here with a high risk of misuse to safeguard.",
    ),
    # 12 Licenses for existing assets
    (
        r"\answerYes{}",
        "Section 2 cites both the descriptor paper and the dataset record for VitalDB and "
        "for MOVER. Appendix A.1 names the terms: VitalDB v1.0.0 under the Creative Commons "
        "Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0) license, openly accessible from PhysioNet, "
        "and MOVER free to download from the UCI Machine Learning Repository for researchers "
        "who sign its data use agreement. Software versions are listed in the "
        "same subsection.",
    ),
    # 13 New assets
    (
        r"\answerYes{}",
        "The analysis code is released at the repository named in Appendix A.1, "
        "under the Apache License 2.0. It carries the documentation and the aggregate result "
        "files needed to inspect and reproduce the reported tables and figures from the "
        "released artifacts. No new dataset, model or checkpoint is released, and no "
        "patient-level data are redistributed.",
    ),
    # 14 Crowdsourcing and human subjects
    (
        r"\answerNA{}",
        "No crowdsourcing was used and no participant was recruited, instructed, contacted "
        "or compensated. The work is a retrospective secondary analysis of already "
        "de-identified records.",
    ),
    # 15 IRB
    (
        r"\answerYes{}",
        "Appendix A.1 records that the Institutional Review Board of Ewha Womans University "
        "Mokdong Hospital granted an exemption from review and waived informed consent for "
        "this secondary analysis (EUMC 2026-08-011). Both source datasets are public and de-identified and were obtained from "
        "their providers under the access and license terms in Appendix A.1. This work added no "
        "data collection and no patient contact.",
    ),
    # 16 LLM usage
    (
        r"\answerNA{}",
        "No large language model is a component of the methods. The five families evaluated "
        "are a transformer over irregularly sampled physiological triplets, an LSTM, "
        "XGBoost, a random forest and logistic regression, and no LLM enters the cohort "
        "construction, the scoring policy, the alert rule or the reference constructions.",
    ),
]


def main() -> None:
    text = TEMPLATE.read_text()

    # The template tells the author to delete the instruction block but keep the heading.
    text, n = re.subn(
        r"%%% BEGIN INSTRUCTIONS %%%.*?%%% END INSTRUCTIONS %%%\n",
        "",
        text,
        flags=re.DOTALL,
    )
    if n != 1:
        raise AssertionError(f"expected 1 instruction block, stripped {n}")

    answers = iter(ANSWERS)
    pending: list[str] = []

    def take_answer(_match: "re.Match[str]") -> str:
        answer, justification = next(answers)
        pending.append(justification)
        return answer

    text, n_ans = re.subn(r"\\answerTODO\{\}", take_answer, text)
    if n_ans != len(ANSWERS):
        raise AssertionError(f"{n_ans} answer slots but {len(ANSWERS)} answers")

    justifications = iter(pending)
    text, n_just = re.subn(
        r"\\justificationTODO\{\}", lambda _m: next(justifications), text
    )
    if n_just != n_ans:
        raise AssertionError(f"{n_just} justification slots but {n_ans} answers")

    # The template leaves the "% Replace by ..." hint next to each filled answer.
    text = re.sub(r"\s*% Replace by \\answerYes\{\}.*", "", text)

    OUT.write_text(text)
    print(f"wrote {OUT} ({n_ans} items filled)")


if __name__ == "__main__":
    main()
