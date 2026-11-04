"""
불법 광고 탐지 Gateway Server (FastAPI)

  [Detector] --REST POST--> [Gateway] --WebSocket push--> [FE(브라우저 대시보드)]
                                 ^                              |
                                 +------ REST review(검수 결과) --+

 - Detector : 수집한 게시물/문자/이미지를 분석해 불법 광고 의심 건을 G/W로 전송
 - Gateway  : 등급 산정, 중복(동일 문구 반복 게시) 판정, FE로 실시간 전달, 검수 상태 관리
 - FE       : 실시간 수신 후 ACK, 담당자가 확정/오탐 판정을 G/W로 회신
              (샘플: fe_dashboard.html / 테스트용 Python 대체: subscriber_client.py)

실행:  uvicorn gateway_server:app --host 0.0.0.0 --port 8000
"""
import asyncio
import logging
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("gateway")

API_KEYS = {"detector-key-001", "subscriber-key-001"}   # 샘플용. 실제는 env/DB
ACK_TIMEOUT_SEC = 5
MAX_RETRY = 3
STORE_MAX = 5000


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
# 1. Inbound 모델 : Detector -> Gateway
# ──────────────────────────────────────────────
Category = Literal[
    "gambling",          # 불법 도박(토토·카지노)
    "illegal_loan",      # 불법 대부·작업대출
    "adult",             # 성매매·음란물
    "drugs",             # 마약류 판매
    "illegal_medicine",  # 의약품 불법 판매
    "counterfeit",       # 위조 상품
    "phishing",          # 피싱·스미싱 유도
]
SourceType = Literal["web", "sns", "community", "sms", "image"]


class Source(BaseModel):
    type: SourceType
    platform: Optional[str] = Field(None, examples=["naver-blog"])
    url: Optional[str] = None
    author: Optional[str] = None
    collected_at: Optional[datetime] = None


class Content(BaseModel):
    text: Optional[str] = Field(None, max_length=4000)
    image_url: Optional[str] = None
    content_hash: str = Field(..., description="정규화 텍스트/이미지의 해시. 반복 게시 판정 키")


class Evidence(BaseModel):
    keywords: list[str] = Field(default_factory=list)      # 탐지된 키워드
    contacts: list[str] = Field(default_factory=list)      # 전화번호·메신저ID·URL 등 연락 수단
    matched_rules: list[str] = Field(default_factory=list)


class ModelInfo(BaseModel):
    name: str = "rule-based"
    version: str = "0.1"


class AdDetection(BaseModel):
    detector_id: str = Field(..., examples=["crawler-01"])
    category: Category
    confidence: float = Field(..., ge=0.0, le=1.0)
    detected_at: datetime
    source: Source
    content: Content
    evidence: Evidence = Field(default_factory=Evidence)
    model: ModelInfo = Field(default_factory=ModelInfo)


class DetectionAccepted(BaseModel):
    event_id: str
    status: Literal["accepted", "duplicate"]
    severity: str
    occurrence: int            # 동일 content_hash 누적 탐지 횟수
    delivered_to: int
    received_at: datetime


class ReviewRequest(BaseModel):
    decision: Literal["confirmed", "false_positive", "reported"]
    reviewer: str
    note: Optional[str] = None




# ──────────────────────────────────────────────
# 1-A. Crawler-style scan response : Detector -> Gateway -> FE
# FE가 기존 크롤러 응답 형식을 그대로 사용할 수 있도록 별도 API 제공
# ──────────────────────────────────────────────
class ScanFinding(BaseModel):
    url: str
    location: str
    text: str
    category: str
    risk_score: int = Field(..., ge=0, le=3)
    evidence: list[str] = Field(default_factory=list)
    reason: str
    risk_level: int = Field(..., ge=1, le=3)
    severity: str
    risk_percent: int = Field(..., ge=0, le=100)
    violation_likelihood: str
    is_exception: bool = False


class DetectorScanResponse(BaseModel):
    status: Literal["success", "error"]
    target_url: str
    count: int = Field(..., ge=0)
    results: list[ScanFinding] = Field(default_factory=list)
    is_exception: bool = False
    error: Optional[str] = None


# ──────────────────────────────────────────────
# 1-B. 분석 결과 모델 : Detector -> Gateway -> FE
# Swagger에서 /api/v1/analysis-results 요청/응답 스키마로 표시됨
# ──────────────────────────────────────────────
Verdict = Literal["HIGH", "MEDIUM", "LOW", "SAFE"]
FindingSeverity = Literal["CRITICAL", "WARNING", "MINOR"]


class AnalysisFinding(BaseModel):
    findingId: int = Field(..., ge=1, examples=[1])
    severity: FindingSeverity
    severityLabel: str = Field(..., examples=["심각"])
    title: str = Field(..., min_length=1, max_length=200)
    reason: str = Field(..., min_length=1, max_length=2000)
    evidenceText: str = Field(..., max_length=2000)
    locationLabel: Optional[str] = Field(None, max_length=200)


class AnalysisResult(BaseModel):
    analysisId: int = Field(..., ge=1, examples=[1])
    targetUrl: str = Field(..., min_length=1, max_length=2048)
    status: Literal["COMPLETED"] = "COMPLETED"
    verdict: Verdict
    verdictLabel: str = Field(..., examples=["위반 가능성 높음"])
    riskScore: int = Field(..., ge=0, le=100)
    summary: str = Field(..., max_length=2000)
    totalFindings: int = Field(..., ge=0)
    findings: list[AnalysisFinding] = Field(default_factory=list)

    @classmethod
    def validate_findings_count(cls, values):
        return values


class AnalysisAccepted(BaseModel):
    status: Literal["accepted"] = "accepted"
    analysisId: int
    deliveredTo: int
    receivedAt: datetime


ANALYSIS_RESULTS: "OrderedDict[int, dict]" = OrderedDict()


# ──────────────────────────────────────────────
# 2. 처리 규칙
# ──────────────────────────────────────────────
SEVERITY_MAP = {
    "drugs": "critical", "phishing": "critical",
    "gambling": "high", "illegal_loan": "high", "adult": "high",
    "illegal_medicine": "medium", "counterfeit": "medium",
}
REVIEW_THRESHOLD = 0.6     # 이 값 미만은 'needs_review'로 표시


EVENTS: "OrderedDict[str, dict]" = OrderedDict()   # event_id -> record
HASH_INDEX: dict[str, str] = {}                    # content_hash -> 최초 event_id


def store(record: dict):
    EVENTS[record["event_id"]] = record
    while len(EVENTS) > STORE_MAX:
        old_id, old = EVENTS.popitem(last=False)
        HASH_INDEX.pop(old["content"]["content_hash"], None)


# ──────────────────────────────────────────────
# 3. Subscriber 연결 관리 (WebSocket Hub)
# ──────────────────────────────────────────────
class Subscriber:
    def __init__(self, ws: WebSocket, client_id: str):
        self.ws = ws
        self.client_id = client_id
        self.categories: set[str] = set()     # 비어 있으면 전체
        self.sources: set[str] = set()
        self.min_confidence: float = 0.0
        self.pending: dict[str, dict] = {}

    def match(self, ev: dict) -> bool:
        # 기존 detector 이벤트와 새 analysis-result payload를 모두 지원
        category = ev.get("category")
        if category is None:
            verdict_to_category = {
                "HIGH": "gambling",
                "MEDIUM": "illegal_loan",
                "LOW": "illegal_medicine",
                "SAFE": "counterfeit",
            }
            category = verdict_to_category.get(ev.get("verdict"), "gambling")
        source = ev.get("source") or {"type": "web"}
        confidence = ev.get("confidence")
        if confidence is None:
            confidence = float(ev.get("riskScore", 0)) / 100.0

        if self.categories and category not in self.categories:
            return False
        if self.sources and source.get("type", "web") not in self.sources:
            return False
        return confidence >= self.min_confidence


class Hub:
    def __init__(self):
        self.subs: dict[str, Subscriber] = {}
        self.lock = asyncio.Lock()

    async def add(self, sub: Subscriber):
        async with self.lock:
            self.subs[sub.client_id] = sub

    async def remove(self, client_id: str):
        async with self.lock:
            self.subs.pop(client_id, None)

    async def publish(self, msg_type: str, ev: dict, need_ack: bool = True) -> int:
        async with self.lock:
            targets = [s for s in self.subs.values() if s.match(ev)]
        count = 0
        loop = asyncio.get_running_loop()
        for s in targets:
            msg = {"msg_type": msg_type, "msg_id": str(uuid.uuid4()),
                   "sent_at": now_utc().isoformat(), "data": ev}
            try:
                await s.ws.send_json(msg)
                if need_ack:
                    s.pending[msg["msg_id"]] = {"msg": msg, "retry": 0, "ts": loop.time()}
                count += 1
            except Exception as e:
                log.warning("send fail %s: %s", s.client_id, e)
        return count

    async def retransmit_loop(self):
        """ACK 미수신 메시지 재전송 (at-least-once)"""
        loop = asyncio.get_running_loop()
        while True:
            await asyncio.sleep(1)
            t = loop.time()
            async with self.lock:
                subs = list(self.subs.values())
            for s in subs:
                for mid, p in list(s.pending.items()):
                    if t - p["ts"] < ACK_TIMEOUT_SEC:
                        continue
                    if p["retry"] >= MAX_RETRY:
                        log.error("drop msg %s -> %s (no ACK)", mid, s.client_id)
                        s.pending.pop(mid, None)
                        continue
                    p["retry"] += 1
                    p["ts"] = t
                    p["msg"]["retry"] = p["retry"]
                    try:
                        await s.ws.send_json(p["msg"])
                        log.info("retransmit %s -> %s (%d)", mid, s.client_id, p["retry"])
                    except Exception:
                        pass


hub = Hub()
app = FastAPI(title="Illegal Ad Detection Gateway", version="1.0.0")

# FE(브라우저)가 다른 origin에서 REST(review/조회)를 호출할 수 있도록 허용. 운영 시 origin 지정
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def _startup():
    asyncio.create_task(hub.retransmit_loop())


def verify_key(x_api_key: str = Header(...)):
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="invalid api key")
    return x_api_key


# ──────────────────────────────────────────────
# 4. REST API
# ──────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "subscribers": len(hub.subs), "events": len(EVENTS),
            "time": now_utc().isoformat()}


@app.post(
    "/api/v1/detector-results",
    summary="Detector 크롤러 분석 결과 전달",
    description="status/target_url/count/results 형식의 크롤러 분석 결과를 받아 FE 구독자에게 같은 데이터 형태로 실시간 전달합니다.",
    status_code=202,
)
async def post_detector_results(payload: DetectorScanResponse, _=Depends(verify_key)):
    if payload.status == "success" and payload.count != len(payload.results):
        raise HTTPException(
            status_code=422,
            detail=f"count({payload.count})와 results 길이({len(payload.results)})가 일치하지 않습니다."
        )

    # FE의 data 필드에는 요청받은 크롤러 응답 JSON을 그대로 전달합니다.
    record = payload.model_dump(mode="json")
    delivered = await hub.publish("detector.scan.completed", record)
    log.info(
        "detector scan received target=%s count=%d -> %d subscribers",
        payload.target_url, payload.count, delivered
    )
    return {
        "status": "accepted",
        "target_url": payload.target_url,
        "count": payload.count,
        "delivered_to": delivered,
        "received_at": now_utc().isoformat(),
    }


@app.post(
    "/api/v1/analysis-results",
    response_model=AnalysisAccepted,
    status_code=202,
    summary="디텍터 분석 결과 수신",
    description="디텍터의 분석 결과 JSON을 검증·저장하고 연결된 FE 구독자에게 WebSocket으로 전달합니다.",
    tags=["Detector ↔ Gateway ↔ FE"],
)
async def post_analysis_result(payload: AnalysisResult, _=Depends(verify_key)):
    record = payload.model_dump(mode="json")
    # 동일 analysisId가 재전송되면 저장 레코드를 갱신하고 다시 전달합니다.
    ANALYSIS_RESULTS[payload.analysisId] = record
    ANALYSIS_RESULTS.move_to_end(payload.analysisId)
    while len(ANALYSIS_RESULTS) > STORE_MAX:
        ANALYSIS_RESULTS.popitem(last=False)

    delivered = await hub.publish("analysis.completed", record)
    log.info(
        "analysis %s verdict=%s risk=%d -> %d subscribers",
        payload.analysisId, payload.verdict, payload.riskScore, delivered
    )
    return AnalysisAccepted(
        analysisId=payload.analysisId,
        deliveredTo=delivered,
        receivedAt=now_utc(),
    )


@app.get(
    "/api/v1/analysis-results",
    summary="분석 결과 목록 조회",
    description="Gateway가 저장한 분석 결과를 최신순으로 조회합니다.",
    tags=["Detector ↔ Gateway ↔ FE"],
)
async def list_analysis_results(
    limit: int = 20,
    _=Depends(verify_key),
):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=422, detail="limit은 1~500 사이여야 합니다.")
    items = list(reversed(list(ANALYSIS_RESULTS.values())))[:limit]
    return {"count": len(items), "items": items}


@app.get(
    "/api/v1/analysis-results/{analysis_id}",
    summary="분석 결과 단건 조회",
    tags=["Detector ↔ Gateway ↔ FE"],
)
async def get_analysis_result(analysis_id: int, _=Depends(verify_key)):
    record = ANALYSIS_RESULTS.get(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="analysis result not found")
    return record


@app.post("/api/v1/detections", response_model=DetectionAccepted, status_code=202)
async def post_detection(ev: AdDetection, _=Depends(verify_key)):
    h = ev.content.content_hash

    # 동일 문구 반복 게시 → 신규 알림 없이 누적 카운트만 증가
    first_id = HASH_INDEX.get(h)
    if first_id and first_id in EVENTS:
        rec = EVENTS[first_id]
        rec["occurrence"] += 1
        rec["last_seen_at"] = now_utc().isoformat()
        if ev.source.url and ev.source.url not in rec["seen_urls"]:
            rec["seen_urls"].append(ev.source.url)
        log.info("duplicate %s (x%d)", first_id, rec["occurrence"])
        return DetectionAccepted(event_id=first_id, status="duplicate", severity=rec["severity"],
                                 occurrence=rec["occurrence"], delivered_to=0, received_at=now_utc())

    event_id = f"ad-{uuid.uuid4().hex[:12]}"
    record = ev.model_dump(mode="json")
    record.update(
        event_id=event_id,
        severity=SEVERITY_MAP[ev.category],
        review_status="needs_review" if ev.confidence < REVIEW_THRESHOLD else "detected",
        occurrence=1,
        seen_urls=[ev.source.url] if ev.source.url else [],
        received_at=now_utc().isoformat(),
        last_seen_at=now_utc().isoformat(),
        review=None,
    )
    store(record)
    HASH_INDEX[h] = event_id

    delivered = await hub.publish("ad.detected", record)
    log.info("new %s %s conf=%.2f -> %d subs", event_id, ev.category, ev.confidence, delivered)
    return DetectionAccepted(event_id=event_id, status="accepted", severity=record["severity"],
                             occurrence=1, delivered_to=delivered, received_at=now_utc())


@app.get("/api/v1/detections")
async def list_detections(limit: int = 20, category: Optional[str] = None,
                          review_status: Optional[str] = None, _=Depends(verify_key)):
    items = [e for e in reversed(EVENTS.values())
             if (not category or e["category"] == category)
             and (not review_status or e["review_status"] == review_status)]
    return {"count": len(items[:limit]), "items": items[:limit]}


@app.get("/api/v1/detections/{event_id}")
async def get_detection(event_id: str, _=Depends(verify_key)):
    if event_id not in EVENTS:
        raise HTTPException(status_code=404, detail="event not found")
    return EVENTS[event_id]


@app.post("/api/v1/detections/{event_id}/review")
async def review_detection(event_id: str, req: ReviewRequest, _=Depends(verify_key)):
    """담당자 검수 결과 반영 → 다른 구독자 화면도 갱신되도록 ad.updated 브로드캐스트"""
    rec = EVENTS.get(event_id)
    if not rec:
        raise HTTPException(status_code=404, detail="event not found")
    rec["review_status"] = req.decision
    rec["review"] = {**req.model_dump(), "reviewed_at": now_utc().isoformat()}
    await hub.publish("ad.updated", rec, need_ack=False)
    log.info("review %s -> %s by %s", event_id, req.decision, req.reviewer)
    return {"event_id": event_id, "review_status": req.decision}


@app.get("/api/v1/stats")
async def stats(_=Depends(verify_key)):
    by_cat: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for e in EVENTS.values():
        by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
        by_status[e["review_status"]] = by_status.get(e["review_status"], 0) + 1
    return {
        "total": len(EVENTS),
        "analysis_results_total": len(ANALYSIS_RESULTS),
        "by_category": by_cat,
        "by_review_status": by_status,
    }


# ──────────────────────────────────────────────
# 5. WebSocket : Gateway <-> Subscriber
# ──────────────────────────────────────────────
@app.websocket("/ws/v1/detections")
async def ws_detections(ws: WebSocket, client_id: str, api_key: str):
    if api_key not in API_KEYS:
        await ws.close(code=4401)
        return
    await ws.accept()
    sub = Subscriber(ws, client_id)
    await hub.add(sub)
    log.info("subscriber connected: %s", client_id)
    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("msg_type")

            if mtype == "subscribe":
                f = msg.get("filters", {})
                sub.categories = set(f.get("categories", []))
                sub.sources = set(f.get("sources", []))
                sub.min_confidence = float(f.get("min_confidence", 0.0))
                await ws.send_json({"msg_type": "subscribed", "filters": {
                    "categories": sorted(sub.categories), "sources": sorted(sub.sources),
                    "min_confidence": sub.min_confidence}})
            elif mtype == "ack":
                sub.pending.pop(msg.get("msg_id"), None)
            elif mtype == "ping":
                await ws.send_json({"msg_type": "pong", "time": now_utc().isoformat()})
            else:
                await ws.send_json({"msg_type": "error", "code": "UNKNOWN_MSG_TYPE", "detail": mtype})
    except WebSocketDisconnect:
        pass
    finally:
        await hub.remove(client_id)
        log.info("subscriber disconnected: %s", client_id)
