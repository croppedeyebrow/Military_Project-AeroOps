# AeroOps Simulator

가상 드론 10대의 텔레메트리를 생성해 backend로 전송하는 Python CLI.
`docs/planning/05_데이터엔지니어링_아키텍처.md`, `docs/roadmap/02_단계_데이터계약_시뮬레이터_Day0304.md` 참고.

## 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m simulator.main run
```

현재는 스텁이며, 2단계에서 실제 비행 시나리오와 오류 주입을 구현한다.
