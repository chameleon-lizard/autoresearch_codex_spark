from __future__ import annotations

from collections import Counter


def _extract_tokens(text: str):
    for token in text.lower().replace(".", " ").replace(",", " ").split():
        token = token.strip()
        if len(token) < 4:
            continue
        yield token


def diagnose_failures(error_rows, max_samples: int = 10) -> str:
    if not error_rows:
        return "No disagreements between candidate predictions and labels."

    positives = [row["text"] for row in error_rows if row["label"] == 0 and row["pred"] == 1]
    negatives = [row["text"] for row in error_rows if row["label"] == 1 and row["pred"] == 0]

    fp_tokens = Counter()
    fn_tokens = Counter()
    for row in positives:
        fp_tokens.update(_extract_tokens(row["text"]))
    for row in negatives:
        fn_tokens.update(_extract_tokens(row["text"]))

    fp_top = ", ".join(tok for tok, _ in fp_tokens.most_common(3)) or "(none)"
    fn_top = ", ".join(tok for tok, _ in fn_tokens.most_common(3)) or "(none)"

    return (
        "Observed disagreements:\n"
        f"- False-positive patterns: {fp_top}\n"
        f"- False-negative patterns: {fn_top}\n"
        f"- Example FP sample count: {len(positives)}\n"
        f"- Example FN sample count: {len(negatives)}\n"
    )
