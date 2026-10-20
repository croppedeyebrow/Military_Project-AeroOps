# C++ 시뮬레이션·Replay

## 적용 위치

Virtual Aircraft, Simulation Clock, Fault Injector, Wire Codec와 대량 Replay를 담당한다.

## 공부할 개념

- C++20 RAII, smart pointer, value semantics
- CMake, compiler warning, sanitizer
- deterministic clock와 fixed-step simulation
- seed 기반 PRNG와 재현성
- 위치·속도·자세·에너지 기초 모델
- binary serialization와 network byte order
- thread, mutex, atomic, bounded queue
- profiling, memory leak, undefined behavior

## 적용 원칙

- Wall Clock과 Simulation Clock을 분리한다.
- 실제 주입 원인은 모델 입력과 분리해 시험 정답으로만 보존한다.
- 업무 권한·승인·통제권 규칙은 C++에 두지 않는다.
- 같은 Seed와 Manifest로 동일한 Scenario를 재현한다.

## 실습

Python Simulator와 같은 Scenario를 실행해 Event 순서와 수치 오차를 비교하고 Address/UndefinedBehavior Sanitizer를 통과한다.
