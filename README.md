# Loki + Grafana + OpenTelemetry Demo

분산 추적(Distributed Tracing)과 중앙화된 로그 수집을 Kubernetes 환경에서 실습하는 데모 프로젝트.

## 아키텍처

```
[ Client ]
    │
    ▼
[ Django (8000) ] ──HTTP + W3C traceparent 헤더──▶ [ FastAPI (8001) ]
    │                                                      │
    │  OTLP gRPC (traces)                                  │  OTLP gRPC (traces)
    ▼                                                      ▼
[ OpenTelemetry Collector (4317) ]◀────────────────────────┘
    │
    └──▶ [ Tempo ] (trace storage)

[ Pod stdout JSON logs ] ──▶ [ Promtail DaemonSet ] ──▶ [ Loki ]
                                                               │
                                                       [ Grafana :3000 ]
                                                       - Loki datasource
                                                       - Tempo datasource
                                                       - Derived Field: trace_id → Tempo
```

**네임스페이스:**
- `observability` – Loki, Tempo, Grafana, OTel Collector, Promtail
- `apps` – Django, FastAPI

## 디렉토리 구조

```
loki-grafana-demo/
├── django-app/          # Django 서비스 (OTel 계측 포함)
├── fastapi-app/         # FastAPI 서비스 (OTel 계측 포함)
├── helm/
│   ├── observability/   # Loki, Tempo, Grafana, Promtail, OTel Collector Helm 차트
│   └── apps/            # Django, FastAPI Helm 차트
└── README.md
```

## 사전 요구사항

- [minikube](https://minikube.sigs.k8s.io/docs/start/) (또는 다른 Kubernetes 클러스터)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm 3](https://helm.sh/docs/intro/install/)

## 실행 방법

### 1. Observability 스택 배포

```bash
# Helm 레포지토리 등록
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# 차트 의존성 다운로드
helm dependency update ./helm/observability

# 배포 (minikube 기준)
helm install observability ./helm/observability \
  -n observability --create-namespace \
  -f helm/observability/values.yaml \
  -f helm/observability/values-local.yaml

# 모든 Pod가 Running 상태가 될 때까지 대기
kubectl get pods -n observability -w
```

### 2. 앱 이미지 빌드 (minikube Docker 환경)

```bash
# minikube의 Docker 데몬 사용 (레지스트리 없이 이미지 사용 가능)
eval $(minikube docker-env)

docker build -t django-app:latest ./django-app
docker build -t fastapi-app:latest ./fastapi-app
```

### 3. 앱 배포

```bash
helm install apps ./helm/apps \
  -n apps --create-namespace \
  -f helm/apps/values.yaml \
  -f helm/apps/values-local.yaml

kubectl get pods -n apps -w
```

### 4. 포트 포워딩

```bash
# Grafana UI
kubectl port-forward svc/observability-grafana 3000:80 -n observability &

# Django 진입점
kubectl port-forward svc/django 8000:8000 -n apps &
```

> minikube NodePort를 사용하는 경우:
> ```bash
> minikube service grafana -n observability --url
> minikube service django -n apps --url
> ```

### 5. 요청 발생

```bash
curl http://localhost:8000/api/hello
# {"django": "ok", "fastapi": {"fastapi": "ok"}}
```

여러 번 요청하면 Loki/Tempo에 충분한 데이터가 쌓입니다.

---

## 검증 체크리스트

Grafana (`http://localhost:3000`, admin/admin)에서 아래를 확인합니다.

| 항목 | 확인 방법 |
|------|-----------|
| ① Django 로그에 `trace_id` 포함 | Explore → Loki → `{app="django"}` |
| ② FastAPI 로그에 동일 `trace_id` 포함 | Explore → Loki → `{app="fastapi"}` |
| ③ Loki에서 두 서비스 로그 확인 | label filter로 `namespace=apps` |
| ④ 로그의 `trace_id` 클릭 → Tempo | Derived Field "TraceID" 링크 클릭 |
| ⑤ Tempo에서 Django→FastAPI span 계층 확인 | Tempo 트레이스 상세 뷰 |

---

## 주요 구현 포인트

### W3C TraceContext 전파
Django의 `RequestsInstrumentor`가 outgoing HTTP 요청에 `traceparent` 헤더를 자동으로 주입합니다.
FastAPI의 `FastAPIInstrumentor`가 이 헤더를 읽어 동일한 trace에 child span을 생성합니다.

### Log–Trace 연결
`api/logging.py` (Django) / `main.py` (FastAPI)의 `OtelJsonFormatter`가 현재 활성 span의
`trace_id`와 `span_id`를 JSON 로그에 포함시킵니다. Promtail이 이 값을 Loki 레이블로 승격시키고,
Grafana의 Derived Field가 해당 `trace_id`를 Tempo 링크로 변환합니다.

### JSON 로그 포맷
```json
{
  "timestamp": "2024-01-01 12:00:00,000",
  "level": "INFO",
  "logger": "api.views",
  "message": "Django received request",
  "service": "django-app",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7"
}
```

---

## 정리

```bash
helm uninstall apps -n apps
helm uninstall observability -n observability
kubectl delete namespace apps observability
```
