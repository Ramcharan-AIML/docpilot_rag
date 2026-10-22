"""LLM-as-judge prompt for the generation eval (step 3.9) and a strict parser for its reply.

ONE judge call per answer does three checks (free-tier tokens are limited):
- faithfulness: split the answer into claims; is each one supported by the context?
  score = supported / total. A claim not in the context = a hallucination.
- correctness: does the answer mean the same as the human reference answer? yes/partly/no
- relevancy: does the answer address the question? 1 to 5
"""

import json
import re

JUDGE_VERSION = "judge-v1"  # change when the prompt changes: part of the cache key

JUDGE_SYSTEM = (
    "You are a strict grader of answers from a documentation assistant. "
    "Judge only from the text you are given. Reply with one JSON object and nothing else."
)

JUDGE_PROMPT = """Context (the ONLY facts the assistant was allowed to use):
{context}

Question: {question}
Reference answer (written by a human): {reference}
Assistant's answer: {answer}

Do three things:
1. "claims": split the assistant's answer into short factual claims (ignore citation marks
   like [1]). For each claim set "supported" to true only if the context states it or
   directly implies it; otherwise false.
2. "correctness": compare the assistant's answer with the reference answer: "yes" (same
   meaning), "partly" (some right, but something important missing or wrong), or "no".
3. "relevancy": an integer 1 to 5: does the answer address the question? (5 = fully)

Reply with JSON only, in this shape:
{{"claims": [{{"claim": "...", "supported": true}}], "correctness": "yes",
 "correctness_reason": "...", "relevancy": 5}}"""

CORRECTNESS_SCORE = {"yes": 1.0, "partly": 0.5, "no": 0.0}


def parse_judge(reply: str) -> dict:
    """Judge reply -> {"claims", "faithfulness", "correctness", "correctness_score", ...}.

    Raises ValueError if the reply is not the JSON we asked for: a broken judge reply must
    never be counted as a score.
    """
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL)  # reasoning models
    start, end = reply.find("{"), reply.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"no JSON object in judge reply: {reply[:200]!r}")
    data = json.loads(reply[start : end + 1])
    claims = data.get("claims")
    correctness = str(data.get("correctness", "")).lower().strip()
    relevancy = data.get("relevancy")
    if not isinstance(claims, list) or correctness not in CORRECTNESS_SCORE:
        raise ValueError(f"judge reply has the wrong shape: {data}")
    if not isinstance(relevancy, int) or not 1 <= relevancy <= 5:
        raise ValueError(f"relevancy must be an integer 1-5: {relevancy!r}")
    supported = sum(1 for claim in claims if claim.get("supported") is True)
    return {
        "claims": claims,
        "faithfulness": round(supported / len(claims), 3) if claims else None,
        "unsupported_claims": [
            c.get("claim", "") for c in claims if c.get("supported") is not True
        ],
        "correctness": correctness,
        "correctness_score": CORRECTNESS_SCORE[correctness],
        "correctness_reason": data.get("correctness_reason", ""),
        "relevancy": relevancy,
    }
