"""
비동기 이벤트 버스 — pub/sub 패턴
- Redis Streams 사용 시도, 실패 시 인메모리 asyncio.Queue로 fallback
- 토픽 기반 구독/발행
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# 지원하는 토픽 목록
TOPICS = [
    "orders.created",           # 새 주문 생성
    "orders.status_changed",    # 주문 상태 변경
    "inventory.updated",        # 재고 변동
    "vehicles.updated",         # 차량 상태/위치 변경
    "anomaly.detected",         # 이상 감지됨
    "priority.recalculated",    # 우선순위 재계산 완료
    "action.requested",         # 액션 실행 요청
    "action.executed",          # 액션 실행 완료
]

# 핸들러 타입: async callable(topic, data)
Handler = Callable[[str, dict], Coroutine[Any, Any, None]]


class AsyncEventBus:
    """
    비동기 이벤트 버스 — Redis Streams 기반, 인메모리 fallback.

    사용법:
        bus = AsyncEventBus(redis_url="redis://localhost:6379")
        await bus.subscribe("orders.created", my_handler)
        await bus.start()  # 구독자 루프 시작
        await bus.publish("orders.created", {"order_code": "ORD-001"})
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self._redis_url = redis_url
        self._redis = None
        self._use_redis = False

        # 토픽별 핸들러 목록
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

        # 인메모리 큐 (fallback)
        self._queues: dict[str, asyncio.Queue] = {}

        # 최근 이벤트 저장 (조회용)
        self._recent_events: dict[str, list[dict]] = defaultdict(list)
        self._max_recent = 500

        # 상태
        self._running = False
        self._consumer_tasks: list[asyncio.Task] = []

    @property
    def is_redis(self) -> bool:
        return self._use_redis

    async def _try_connect_redis(self):
        """Redis 연결 시도"""
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            await self._redis.ping()
            self._use_redis = True
            logger.info("AsyncEventBus: Redis 연결 성공")
        except Exception as e:
            logger.warning(f"AsyncEventBus: Redis 연결 실패 ({e}) — 인메모리 모드")
            self._redis = None
            self._use_redis = False

    async def subscribe(self, topic: str, handler: Handler):
        """토픽에 핸들러를 구독 등록한다."""
        self._handlers[topic].append(handler)
        # 인메모리 모드용 큐 준비
        if topic not in self._queues:
            self._queues[topic] = asyncio.Queue(maxsize=10000)
        logger.debug(f"구독 등록: {topic} → {handler.__qualname__}")

    async def publish(self, topic: str, data: dict):
        """이벤트를 토픽에 발행한다."""
        event = {
            "topic": topic,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 최근 이벤트 저장
        self._recent_events[topic].append(event)
        if len(self._recent_events[topic]) > self._max_recent:
            self._recent_events[topic] = self._recent_events[topic][-self._max_recent:]

        if self._use_redis and self._redis:
            try:
                serialized = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                              for k, v in data.items()}
                serialized["_timestamp"] = event["timestamp"]
                await self._redis.xadd(topic, serialized, maxlen=1000)
            except Exception as e:
                logger.error(f"Redis publish 실패 ({topic}): {e}")
                # fallback으로 인메모리 큐에 넣기
                await self._enqueue_inmemory(topic, event)
        else:
            await self._enqueue_inmemory(topic, event)

    async def _enqueue_inmemory(self, topic: str, event: dict):
        """인메모리 큐에 이벤트를 넣는다."""
        if topic not in self._queues:
            self._queues[topic] = asyncio.Queue(maxsize=10000)
        try:
            self._queues[topic].put_nowait(event)
        except asyncio.QueueFull:
            # 오래된 이벤트 버리고 새 이벤트 추가
            try:
                self._queues[topic].get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._queues[topic].put_nowait(event)

    async def _inmemory_consumer(self, topic: str):
        """인메모리 큐 소비자 루프"""
        queue = self._queues.get(topic)
        if not queue:
            return

        while self._running:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                await self._dispatch(topic, event["data"])
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"인메모리 소비자 에러 ({topic}): {e}")
                await asyncio.sleep(0.1)

    async def _redis_consumer(self, topic: str):
        """Redis Streams 소비자 루프"""
        last_id = "$"  # 새 메시지만 구독
        while self._running:
            try:
                results = await self._redis.xread(
                    {topic: last_id}, count=10, block=1000
                )
                for stream_name, messages in results:
                    for msg_id, msg_data in messages:
                        last_id = msg_id
                        # _timestamp 필드 제거 후 전달
                        data = {k: v for k, v in msg_data.items() if k != "_timestamp"}
                        # JSON 문자열 복원 시도
                        for k, v in data.items():
                            try:
                                data[k] = json.loads(v)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        await self._dispatch(topic, data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Redis 소비자 에러 ({topic}): {e}")
                await asyncio.sleep(1.0)

    async def _dispatch(self, topic: str, data: dict):
        """핸들러들에게 이벤트를 전달한다."""
        handlers = self._handlers.get(topic, [])
        for handler in handlers:
            try:
                await handler(topic, data)
            except Exception as e:
                logger.error(f"핸들러 에러 ({topic}, {handler.__qualname__}): {e}")

    async def start(self):
        """이벤트 버스 시작 — 구독자 루프를 생성한다."""
        await self._try_connect_redis()
        self._running = True

        # 구독이 등록된 토픽마다 소비자 태스크 생성
        for topic in self._handlers:
            if self._use_redis:
                task = asyncio.create_task(
                    self._redis_consumer(topic),
                    name=f"redis-consumer-{topic}",
                )
            else:
                # 인메모리 큐 확보
                if topic not in self._queues:
                    self._queues[topic] = asyncio.Queue(maxsize=10000)
                task = asyncio.create_task(
                    self._inmemory_consumer(topic),
                    name=f"inmemory-consumer-{topic}",
                )
            self._consumer_tasks.append(task)

        logger.info(
            f"AsyncEventBus 시작: {len(self._consumer_tasks)}개 소비자 "
            f"({'Redis' if self._use_redis else '인메모리'})"
        )

    async def stop(self):
        """이벤트 버스 중지"""
        self._running = False
        for task in self._consumer_tasks:
            task.cancel()
        if self._consumer_tasks:
            await asyncio.gather(*self._consumer_tasks, return_exceptions=True)
        self._consumer_tasks = []

        if self._redis:
            await self._redis.aclose()
            self._redis = None

        logger.info("AsyncEventBus 중지 완료")

    def get_recent(self, topic: str, count: int = 10) -> list[dict]:
        """최근 이벤트 조회 (동기)"""
        return self._recent_events.get(topic, [])[-count:]
