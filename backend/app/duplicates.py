import difflib
import re
from dataclasses import dataclass


@dataclass
class DuplicatePair:
    question_id_1: str
    question_id_2: str
    text_1: str
    text_2: str
    similarity: float
    reason: str


def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return " ".join(cleaned.split())


def find_duplicates(questions: list[dict], threshold: float = 0.80) -> list[DuplicatePair]:
    """Finds potential duplicate questions without automatic deletion.
    
    questions: list of dicts with keys 'id' and 'question_text'.
    threshold: similarity score cutoff (0.0 - 1.0).
    """
    duplicates: list[DuplicatePair] = []
    n = len(questions)

    for i in range(n):
        for j in range(i + 1, n):
            q1 = questions[i]
            q2 = questions[j]

            t1 = _normalize(q1["question_text"])
            t2 = _normalize(q2["question_text"])

            if not t1 or not t2:
                continue

            # Exact match
            if t1 == t2:
                duplicates.append(
                    DuplicatePair(
                        question_id_1=q1["id"],
                        question_id_2=q2["id"],
                        text_1=q1["question_text"],
                        text_2=q2["question_text"],
                        similarity=1.0,
                        reason="Exact textual match (excluding punctuation/casing)",
                    )
                )
                continue

            # Fuzzy sequence similarity
            matcher = difflib.SequenceMatcher(None, t1, t2)
            similarity = matcher.ratio()

            # Token overlap check (Jaccard similarity)
            tokens1 = set(t1.split())
            tokens2 = set(t2.split())
            intersection = tokens1.intersection(tokens2)
            union = tokens1.union(tokens2)
            jaccard = len(intersection) / len(union) if union else 0.0

            overall_score = round(max(similarity, jaccard), 3)
            if overall_score >= threshold:
                duplicates.append(
                    DuplicatePair(
                        question_id_1=q1["id"],
                        question_id_2=q2["id"],
                        text_1=q1["question_text"],
                        text_2=q2["question_text"],
                        similarity=overall_score,
                        reason=f"High phrasing similarity ({overall_score:.0%})",
                    )
                )

    return duplicates
