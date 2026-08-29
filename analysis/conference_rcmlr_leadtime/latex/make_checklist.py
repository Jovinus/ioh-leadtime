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
        "The abstract and Section 1 state the four contributions and their scope. They "
        "distinguish the observed lead--window association from what the upward-biased "
        "shuffle can establish, treat low directedness as descriptive rather than causal, "
        "and state that the paper measures neither clinician comprehension nor physiology.",
    ),
    # 2 Limitations
    (
        r"\answerYes{}",
        "Section 7 is a separate limitations section covering the retrospective design, the "
        "single outcome definition, single training seed and operating-point family, the "
        "pipeline-specific results, null selection and upward bias, the single clinical "
        "domain, and the unvalidated communication and reporting proposals.",
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
        "procedures; and the analysis code is released at the anonymized repository "
        "Appendix A.1 names. Bit-for-bit reproduction from raw data is not supported here, "
        "because neither dataset may be redistributed and the cached per-minute scores the "
        "analyses read are derived patient-level data governed by the same agreements, so "
        "they are not in the repository and a reader must obtain the data themselves. We "
        "claim the first and not the second.",
    ),
    # 5 Open access to data and code
    (
        r"\answerYes{}",
        "The analysis code is released at an anonymized repository under the Apache License "
        "2.0, which Appendix A.1 names, together with the aggregate result files behind every "
        "table and figure, so "
        "the table and figure checks run from the repository as shipped. The datasets are "
        "not redistributed there and cannot be: VitalDB is under a Creative Commons "
        "Attribution-NonCommercial-ShareAlike 4.0 International license and a data use "
        "agreement and MOVER is under a data use agreement, and the cached per-minute scores "
        "are derived patient-level data governed by the same agreements. Both are obtained "
        "from their own project sites once access is granted, as Appendix A.1 records, and "
        "Appendix A.1 specifies the construction to the level a reimplementation needs.",
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
        "2,000 replicates; permutation nulls use 1,000 replicates and are reported as the "
        "2.5th and 97.5th percentiles of the null distribution rather than as symmetric "
        "error bars. Appendix A.18 records the multiplicity family and its "
        "Benjamini--Hochberg adjustment, and Appendix A.19 the seeds.",
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
        "de-identified data obtained under the providers' data use agreements, with an "
        "institutional review board exemption and consent waiver recorded in Section 2 and "
        "Appendix A.1, and it proposes no model for clinical use.",
    ),
    # 10 Broader impacts
    (
        r"\answerYes{}",
        "The paper's subject is a negative societal impact of current practice: a reported "
        "median alert lead time invites a warning-time interpretation while remaining "
        "strongly coupled to observation length, which can overstate what a deployed monitor offers. "
        "Section 5 shows that two natural repairs fail, including one whose sensitivity cost "
        "is quantified, and Section 6.2 proposes four reporting items as the mitigation. "
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
        "for MOVER. Appendix A.1 names the terms: VitalDB under a Creative Commons "
        "Attribution-NonCommercial-ShareAlike 4.0 International license with a data use "
        "agreement, and MOVER free to download from the UCI Machine Learning Repository for "
        "researchers who sign its data use agreement. Software versions are listed in the "
        "same subsection.",
    ),
    # 13 New assets
    (
        r"\answerYes{}",
        "The analysis code is released at the anonymized repository named in Appendix A.1, "
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
        "Section 2 records that an institutional review board granted an exemption from "
        "review and waived informed consent for this secondary analysis of publicly "
        "available de-identified data, with the institution and protocol number withheld for "
        "anonymous review. Appendix A.1 records that each source collection carried its own "
        "review-board approval with consent waived after de-identification, and that this "
        "work added no data collection and no patient contact.",
    ),
    # 16 LLM usage
    (
        r"\answerNA{}",
        "No large language model is a component of the methods. The five families evaluated "
        "are a transformer over irregularly sampled physiological triplets, an LSTM, "
        "XGBoost, a random forest and logistic regression, and no LLM enters the cohort "
        "construction, the scoring policy, the alert rule or the null constructions. "
        "Generative AI was used only for English language editing of author-written text, "
        "which the policy states does not require declaration.",
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
