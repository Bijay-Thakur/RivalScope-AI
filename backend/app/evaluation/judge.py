"""LLM-as-judge grounding (ported from evals/). Reference-free faithfulness:
does the cited SOURCE TEXT support the CLAIM? Judge model defaults to a stronger
tier than synthesis (settings.judge_model) to reduce self-eval bias."""

import asyncio
import logging

from pydantic import BaseModel, Field

from app.core.config import settings
from app.evaluation.schemas import Verdict
from app.observability.tracing import traceable

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM_PROMPT = (
    "You are a strict grounding judge. Given a CLAIM and the SOURCE TEXT it cites, "
    "decide ONLY from the source text whether it supports the claim.\n"
    "SUPPORTED = fully entailed by the source text.\n"
    "PARTIAL = source text partly supports it.\n"
    "UNSUPPORTED = source text is silent on the claim.\n"
    "CONTRADICTED = source text states the opposite.\n"
    "Ignore all outside knowledge — judge the given text only, nothing else. "
    "Keep rationale to one terse sentence."
)


class _JudgeVerdict(BaseModel):
    verdict: str = Field(description="one of: supported, partial, unsupported, contradicted")
    rationale: str
    judge_confidence: float = Field(ge=0.0, le=1.0)


def _get_judge_llm(model: str):
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=model,
        temperature=0.0,
        google_api_key=settings.google_api_key or settings.gemini_api_key,
    )
    return llm.with_structured_output(_JudgeVerdict)


@traceable(run_type="llm", name="judge_claim")
async def judge_claim(
    claim: str,
    source_title: str,
    source_url: str,
    source_text: str,
    model: str,
) -> tuple[Verdict, str, float]:
    user_message = (
        f"CLAIM: {claim}\n\n"
        f"SOURCE TITLE: {source_title}\n"
        f"SOURCE URL: {source_url}\n"
        f"SOURCE TEXT:\n{source_text or '(empty)'}"
    )
    try:
        llm = _get_judge_llm(model)
        result: _JudgeVerdict = await llm.ainvoke(
            [
                {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ]
        )
        verdict = Verdict(result.verdict.strip().lower())
        return verdict, result.rationale, result.judge_confidence
    except Exception as exc:
        logger.warning("judge_claim failed [%s] — defaulting to UNSUPPORTED.", type(exc).__name__)
        return Verdict.UNSUPPORTED, f"Judge error: {type(exc).__name__}", 0.0


async def judge_claims(
    items: list[dict],
    model: str,
    max_concurrency: int = 3,
) -> list[tuple[Verdict, str, float]]:
    if not items:
        return []

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _bounded(item: dict) -> tuple[Verdict, str, float]:
        async with semaphore:
            return await judge_claim(
                claim=item["claim"],
                source_title=item["source_title"],
                source_url=item["source_url"],
                source_text=item["source_text"],
                model=model,
            )

    return await asyncio.gather(*(_bounded(item) for item in items))
