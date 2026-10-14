"""Rule-based categorisation.

The approach is intentionally simple and explainable:

* each category has *strong* keywords (clear signals, weight 3 by default) and
  *weak* keywords (supporting context, weight 1);
* keywords are matched as whole words / phrases, case-insensitively;
* the category whose strong keyword appears in the opening words of the
  summary gets a small bonus, because the leading verb usually states what the
  requester actually wants ("Connect ...", "Automate ...", "Publish ...");
* the highest score wins. No match means ``Uncategorised``; a tie or a weak
  match is reported as low confidence so a person can check it.

Every result carries the matched keywords and a one-line rationale so the
decision can be shown to the requester or reviewer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from .models import CategoryResult


@dataclass(frozen=True)
class _Keyword:
    text: str
    weight: int
    strong: bool
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class _Category:
    name: str
    keywords: tuple[_Keyword, ...]


def _compile_keyword(text: str) -> re.Pattern[str]:
    # Whole-word / whole-phrase match: "api" must not match "rapid".
    return re.compile(r"(?<!\w)" + re.escape(text.lower()) + r"(?!\w)", re.IGNORECASE)


@lru_cache(maxsize=8)
def _compile_categories(categories_json: str) -> tuple[_Category, ...]:
    import json

    cfg = json.loads(categories_json)
    strong_weight = int(cfg.get("strong_weight", 3))
    weak_weight = int(cfg.get("weak_weight", 1))
    compiled: list[_Category] = []
    for entry in cfg["categories"]:
        keywords: list[_Keyword] = []
        for text in entry.get("strong", []):
            keywords.append(_Keyword(text, strong_weight, True, _compile_keyword(text)))
        for text in entry.get("weak", []):
            keywords.append(_Keyword(text, weak_weight, False, _compile_keyword(text)))
        compiled.append(_Category(entry["name"], tuple(keywords)))
    return tuple(compiled)


def category_names(rules: dict[str, Any]) -> list[str]:
    cfg = rules["categorisation"]
    return [c["name"] for c in cfg["categories"]] + [cfg.get("fallback_category", "Uncategorised")]


def categorise(summary: str, rules: dict[str, Any]) -> CategoryResult:
    import json

    cfg = rules["categorisation"]
    fallback = cfg.get("fallback_category", "Uncategorised")
    text = " ".join((summary or "").split())
    if not text:
        return CategoryResult(fallback, "none", 0, [], {}, "No request summary to categorise")

    categories = _compile_categories(json.dumps(cfg, sort_keys=True))
    leading_words = int(cfg.get("leading_words", 3))
    leading_bonus = int(cfg.get("leading_verb_bonus", 2))
    lead_text = " ".join(text.lower().split()[:leading_words])

    scores: dict[str, int] = {}
    matched: dict[str, list[str]] = {}
    leading: set[str] = set()
    for category in categories:
        score = 0
        hits: list[str] = []
        leads = False
        for keyword in category.keywords:
            if keyword.pattern.search(text):
                score += keyword.weight
                hits.append(keyword.text)
                if keyword.strong and keyword.pattern.search(lead_text):
                    leads = True
        if leads:
            score += leading_bonus
            leading.add(category.name)
        scores[category.name] = score
        matched[category.name] = hits

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_name, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score == 0:
        return CategoryResult(fallback, "none", 0, [], scores, "No category keywords found in the summary")

    margin = best_score - second_score
    minimum = int(cfg.get("minimum_confident_score", 3))
    high_margin = int(cfg.get("high_confidence_margin", 3))
    if margin == 0:
        confidence = "low"
        tied = [name for name, score in ranked if score == best_score]
        # Tie-break: the category named by the opening verb, if exactly one is.
        tied_leaders = [name for name in tied if name in leading]
        if len(tied_leaders) == 1:
            best_name = tied_leaders[0]
            rationale = f"Tie between {', '.join(tied)} (score {best_score}); picked {best_name} because the request opens with its keyword"
        else:
            rationale = f"Tie between {', '.join(tied)} (score {best_score}); picked {best_name} by rule order"
    elif best_score < minimum:
        confidence = "low"
        rationale = f"Weak match for {best_name} (score {best_score}): {', '.join(matched[best_name])}"
    else:
        confidence = "high" if margin >= high_margin else "medium"
        runner_up = ranked[1][0] if second_score else None
        rationale = f"{best_name} scored {best_score} on: {', '.join(matched[best_name])}"
        if runner_up:
            rationale += f" (next: {runner_up} {second_score})"

    return CategoryResult(best_name, confidence, best_score, matched[best_name], scores, rationale)
