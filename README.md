# 한국타이어 출하물류 AI 에이전트 시스템

실시간 출하 물류 우선순위 결정 및 실행을 위한 AI 에이전트 데모 시스템입니다.
OODA Loop(Observe→Orient→Decide→Act) 기반으로 물류 이상 상황을 자동 감지하고,
원인을 분석하며, 우선순위를 재계산하고, 적절한 액션을 실행합니다.

## 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│                    Frontend (React)                       │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │Operations│  │  OODA Loop   │  │  Actions & Alerts  │  │
│  │  Panel   │  │  Viz + Agent │  │  Feed + Approval   │  │
│  │  (30%)   │  │  Timeline    │  │  Queue             │  │
│  │          │  │  (45%)       │  │  (25%)             │  │
│  └──────────┘  └──────────────┘  └────────────────────┘  │
│                    WebSocket ↕ REST API                   │
└──────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                       │
│                                                          │
│  ┌─────────────────── OODA Pipeline ──────────────────┐  │
│  │  Monitor    → Anomaly     → Priority   → Action    │  │
│  │  (Observe)    (Orient)      (Decide)     (Act)     │  │
│  │  5 Rules      LLM/Tmpl     Scoring      Auto/     │  │
│  │  Detection    Analysis      Model       Approval   │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │  Simulators  │  │  Event   │  │  SQLite + Redis   │   │
│  │  Order/Veh/  │  │  Bus     │  │  (fallback:       │   │
│  │  Anomaly     │  │  (Async) │  │   in-memory)      │   │
│  └──────────────┘  └──────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| **Backend** | Python 3.13, FastAPI, SQLAlchemy, SQLite |
| **AI Agent** | Claude API (선택), 템플릿 기반 Fallback |
| **Event Bus** | Redis Streams (선택), In-memory Queue Fallback |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS v4 |
| **Charts** | Recharts, Custom SVG (OODA Loop) |
| **Icons** | Lucide React |
| **Realtime** | WebSocket (native) |
| **Container** | Docker Compose (선택) |

## 실행 방법

### 방법 1: 로컬 실행 (권장)

**Backend 실행:**
```bash
cd backend

# Python 가상환경 (선택)
python -m venv venv && source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 초기 데이터 생성
python seed_data.py

# 서버 시작
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend 실행 (새 터미널):**
```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 시작
npm run dev
```

브라우저에서 **http://localhost:5173** 을 열면 대시보드를 확인할 수 있습니다.

### 방법 2: Docker Compose

```bash
# 프로젝트 루트에서
docker compose up --build

# 접속: http://localhost:3000 (프론트엔드)
#        http://localhost:8000 (백엔드 API)
```

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///logistics.db` | 데이터베이스 경로 |
| `REDIS_URL` | `redis://localhost:6379` | Redis 접속 URL (없으면 in-memory fallback) |
| `ANTHROPIC_API_KEY` | _(빈 문자열)_ | Claude API 키 **(선택사항)** — 없어도 템플릿 기반으로 정상 동작 |
| `LLM_MODEL` | `claude-sonnet-4-5-20250929` | 사용할 Claude 모델 |

> **참고:** `ANTHROPIC_API_KEY`가 없어도 전체 시스템이 정상 동작합니다. AI 분석이 템플릿 기반으로 자동 전환됩니다.

## 데모 실행

### 자동 데모 (권장)
1. 대시보드 접속 후, 헤더 중앙의 **▶ Demo** 버튼 클릭
2. 5단계 시나리오가 자동으로 진행됩니다:
   - Phase 0: 정상 운영 (30초)
   - Phase 1: 주문 급증 (60초)
   - Phase 2: 차량 고장 (60초)
   - Phase 3: SLA 위반 위험 (45초)
   - Phase 4: 정상 복구 (15초)
3. 진행 상태는 헤더의 프로그레스 바로 확인

### 수동 데모
헤더 우측의 드롭다운에서 이상 시나리오를 선택하고 **Inject** 클릭:
- **Order Surge**: 20~30건 주문이 동시 생성
- **Vehicle Breakdown**: 차량 1대 고장
- **Stock Shortage**: 재고 부족 발생
- **SLA Risk**: VIP 고객 납기 위험
- **Dock Congestion**: 도크 병목

### 데이터 초기화
헤더의 ↻ (Reset) 버튼으로 데이터를 초기 상태로 복원할 수 있습니다.

## 주요 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/health` | 시스템 상태 확인 |
| GET | `/api/dashboard/overview` | 대시보드 전체 현황 |
| GET | `/api/orders` | 주문 목록 |
| GET | `/api/agents/events` | 에이전트 이벤트 목록 |
| GET | `/api/agents/timeline` | 에이전트 타임라인 |
| GET | `/api/actions/pending` | 승인 대기 액션 |
| POST | `/api/actions/{id}/approve` | 액션 승인 |
| POST | `/api/actions/{id}/reject` | 액션 거절 |
| POST | `/api/simulation/trigger-anomaly` | 이상 시나리오 트리거 |
| PUT | `/api/simulation/speed` | 시뮬레이션 속도 변경 |
| POST | `/api/simulation/start-demo` | 데모 시나리오 시작 |
| GET | `/api/simulation/demo-status` | 데모 진행 상태 |
| POST | `/api/simulation/stop-demo` | 데모 중지 |
| POST | `/api/simulation/reset` | 데이터 초기화 |
| WS | `/ws/realtime` | 실시간 WebSocket |

## OODA Loop 에이전트

| 단계 | 에이전트 | 역할 |
|------|---------|------|
| **Observe** | Monitor Agent | 5가지 규칙으로 이상 감지 (주문급증, 차량고장, 재고부족, SLA위험, 도크병목) |
| **Orient** | Anomaly Agent | 이상 원인 분석 + 영향도 평가 (Claude API 또는 템플릿) |
| **Decide** | Priority Agent | 다요소 우선순위 재계산 (고객등급 25%, 긴급도 30%, 제품등급 15%, 재고 15%, 이상영향 15%) |
| **Act** | Action Agent | 신뢰도 기반 실행 (AUTO ≥0.85, 승인대기 ≥0.60, 에스컬레이션 <0.60) |
