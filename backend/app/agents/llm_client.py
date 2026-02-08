"""
LLM 클라이언트 — Claude API 호출 래퍼.
- API 키가 없으면 None 반환 (호출자가 fallback 처리).
- 비동기 호출 지원.
"""

import asyncio
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_client = None
_available = False


def _init_client():
    """Anthropic 클라이언트 초기화 (lazy)"""
    global _client, _available
    if _client is not None:
        return

    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY 미설정 — LLM 기능 비활성화 (템플릿 fallback 사용)")
        _available = False
        return

    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        _available = True
        logger.info("Claude API 클라이언트 초기화 완료")
    except Exception as e:
        logger.error(f"Claude API 클라이언트 초기화 실패: {e}")
        _available = False


def is_available() -> bool:
    """LLM 호출이 가능한지 확인"""
    _init_client()
    return _available


async def call_llm(system_prompt: str, user_prompt: str) -> str | None:
    """
    Claude API 호출. 실패 시 None 반환.
    블로킹 호출을 executor에서 실행한다.
    """
    _init_client()
    if not _available or _client is None:
        return None

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: _client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ),
        )
        text = response.content[0].text
        logger.info(f"LLM 응답 수신 ({len(text)} chars, {response.usage.input_tokens}+{response.usage.output_tokens} tokens)")
        return text

    except Exception as e:
        logger.error(f"LLM 호출 실패: {e}")
        return None
