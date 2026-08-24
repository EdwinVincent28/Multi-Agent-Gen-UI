import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

def extract_text_content(content):
    """
    Normalizes an LLM response's .content into a plain string.

    Groq always returned a flat string. Gemini (via ChatGoogleGenerativeAI)
    can return .content as a list of parts instead — e.g. separate
    reasoning/thought and answer segments — depending on the model and
    response. Every node that does regex/string ops on response.content
    should route through this first, or things like re.sub(...) will fail
    with "expected string or bytes-like object, got 'list'" whenever Gemini
    returns a multi-part response.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))
        return "".join(parts)
    return str(content) if content is not None else ""

def get_llm(temperature=0.0, thinking_level="low"):
    """
    Initializes the Google Gemini client for text/code generation
    (analyst, frontend_engineer, evaluator nodes).

    Switched from Groq: the connected Groq org was capped at 8,000 TPM on
    every model tried, which repeatedly 413'd even after trimming prompts
    and capping output. Gemini's free tier on the same GEMINI_API_KEY
    already used for vision gives a far higher TPM ceiling.

    max_output_tokens was originally set to 3000, then 8192, both as
    leftover defensive caps from the Groq era / the old gemini-1.5-flash
    default. Neither number reflects this model's actual capability:
    gemini-3.6-flash supports up to 65,536 output tokens. Capping it
    artificially low was actively truncating generated React components
    mid-expression, producing invalid JSX that failed in the live preview.
    Set to the model's real ceiling — there's no cost or latency reason to
    cap it lower on the free tier, and a dashboard component should be
    allowed to be exactly as long as it needs to be.

    NOTE: a 429 RESOURCE_EXHAUSTED error mentioning
    "generate_content_free_tier_requests" with quotaId
    "GenerateRequestsPerDayPerProjectPerModel-FreeTier" is a REQUESTS-PER-DAY
    quota, not per-minute — retry/backoff cannot fix it, the quota simply
    won't refill until it resets (~midnight Pacific).

    ANOTHER TRUNCATION CAUSE: Gemini 3-series models (gemini-3.6-flash
    included) do internal "thinking" by default, controlled by
    thinking_level ('low'/'medium'/'high'), defaulting to 'high' if unset.
    Thinking tokens count against the SAME max_output_tokens budget as the
    visible answer. thinking_level="low" fixed the truncation, but it's a
    trade-off, not a free win: it also cuts reasoning depth, which showed
    up as poor fidelity to the vision blueprint — frontend_engineer was
    generating generic stacked-card layouts instead of actually mapping
    the blueprint's grid/colSpan/chart-type JSON onto matching JSX. That
    kind of structured translation needs more reasoning than a markdown
    summary or a pass/fail check does. thinking_level is now a parameter
    so callers can ask for more depth where it's worth the extra tokens —
    frontend_engineer should pass "medium"; analyst/evaluator can stay at
    the default "low" since their tasks are more mechanical.
    """

    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash"),
        temperature=temperature,
        max_output_tokens=65536,
        thinking_level=thinking_level,
        api_key=os.getenv("GEMINI_API_KEY")
    ).with_retry(
        stop_after_attempt=5,
        wait_exponential_jitter=True
    )

def get_vision_llm(temperature=0.0):
    """
    Initializes the Google Gemini client for vision (wireframe extraction).
    Same account constraint as get_llm() — gemini-2.5-flash 404s on this
    account, so this defaults to gemini-3.6-flash too. thinking_level
    capped for the same reason as get_llm().
    """
    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_VISION_MODEL", "gemini-3.6-flash"),
        temperature=temperature,
        thinking_level="low",
        api_key=os.getenv("GEMINI_API_KEY")
    ).with_retry(
        stop_after_attempt=5,
        wait_exponential_jitter=True
    )