from loguru import logger


def extract_tokens_used(response) -> int:
    """
    Extracts token usage from an LLM response
    """
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        return response.usage_metadata.get("total_tokens", 0)
    if hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
        return response.response_metadata["token_usage"].get("total_tokens", 0)
    return 0


DEFAULT_RESPONSE_PREVIEW_CHARS = 500


def record_node_telemetry(
    state_telemetry: dict,
    node_name: str,
    elapsed_time: float,
    tokens_used: int,
    response_text: str = None,
    preview_chars: int = DEFAULT_RESPONSE_PREVIEW_CHARS,
) -> dict:
    """
    Logs a standalone completion line for ONE node 
    """
    telemetry = dict(state_telemetry or {})

    logger.info(
        f"[TELEMETRY] {node_name} completed — latency: {elapsed_time:.2f}s, tokens: {tokens_used}"
    )

    if response_text is not None:
        if len(response_text) > preview_chars:
            preview = response_text[:preview_chars] + f"... [truncated, full length: {len(response_text)} chars]"
        else:
            preview = response_text
        logger.debug(f"[RESPONSE] {node_name} output:\n{preview}")

    telemetry["total_latency"] = round(telemetry.get("total_latency", 0.0) + elapsed_time, 2)
    telemetry["total_tokens"] = telemetry.get("total_tokens", 0) + tokens_used

    return telemetry