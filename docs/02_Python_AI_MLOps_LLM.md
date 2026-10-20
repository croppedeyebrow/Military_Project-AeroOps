# Python·AI·MLOps·LLM

## 적용 위치

Feature Engineering, 이상 탐지, MLflow, Hybrid RAG, 로컬 LLM 추론과 평가를 담당한다. 실시간 Command 경로에는 참여하지 않는다.

## 공부할 개념

- NumPy/Pandas 시계열 Window Feature
- 결측·지연·불규칙 Sampling 처리
- 규칙, EWMA, Isolation Forest
- 시간·비행·기체 단위 데이터 분할과 Leakage
- Precision/Recall, False Alarm, 탐지 지연
- MLflow Tracking·Registry·Alias·Lineage
- Tokenization, Embedding, Quantization, GGUF
- FTS·Vector Retrieval·RRF·Reranking
- Structured Output, Faithfulness, Prompt Injection

## 적용 원칙

- 시뮬레이터의 실제 장애 정답을 운용 시점 Feature에 넣지 않는다.
- 입력 품질이 낮으면 모델 판단을 보류한다.
- 분석 결과에는 근거 Event·문서·모델·Prompt Version을 포함한다.
- 모델 장애 시 Kotlin 규칙 엔진으로 Fallback한다.

## 실습

동일 Replay Dataset에서 규칙·EWMA·Isolation Forest의 오경보와 탐지 지연을 비교하고 승인 Alias 변경·Rollback을 수행한다.
