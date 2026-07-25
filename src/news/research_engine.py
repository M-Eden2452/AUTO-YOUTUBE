from __future__ import annotations

import re
from typing import Any

from .models import NewsJob


def build_research(job: NewsJob, article: dict[str, Any]) -> dict[str, Any]:
    text = article.get("text") or article.get("title") or job.topic
    sentences = split_sentences(text)
    claims = []
    for index, sentence in enumerate(sentences[:8], start=1):
        claim_type = classify_claim(sentence)
        claims.append(
            {
                "claim_id": f"claim_{index:03d}",
                "text": sentence,
                "claim_type": claim_type,
                "confidence": 0.75 if claim_type in {"reported", "hypothesis"} else 0.85,
                "source_urls": [url for url in job.source_urls if url],
                "source_excerpt": sentence[:240],
                "safe_for_script": claim_type not in {"unsupported"},
            }
        )
    if not claims:
        claims.append(
            {
                "claim_id": "claim_001",
                "text": article.get("title") or job.topic,
                "claim_type": "reported",
                "confidence": 0.6,
                "source_urls": [url for url in job.source_urls if url],
                "source_excerpt": article.get("title") or job.topic,
                "safe_for_script": True,
            }
        )
    return {
        "topic": job.topic or article.get("title", ""),
        "summary": summarize(sentences, article.get("title", "")),
        "claims": claims,
        "unknowns": [],
        "contradictions": [],
        "primary_source_candidates": [article["primary_source_candidate"]] if article.get("primary_source_candidate") else [],
    }


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+", text.replace("\n", " "))
    return [part.strip() for part in parts if len(part.strip()) > 8]


def classify_claim(sentence: str) -> str:
    lowered = sentence.lower()
    if any(word in lowered for word in ("возможно", "предполага", "гипотез", "может быть", "could", "may ")):
        return "hypothesis"
    if any(word in lowered for word in ("сообщ", "reported", "according")):
        return "reported"
    return "confirmed"


def summarize(sentences: list[str], title: str) -> str:
    if sentences:
        return " ".join(sentences[:2])
    return title

