# env

이 폴더는 **동적 팔레트 적재 문제의 환경(environment)** 을 정의한다.

현재 단계의 env는 실제 휴리스틱 배치나 planner 의사결정보다 앞서,
논문 실험을 위한 **시뮬레이션 골격**을 만드는 역할을 한다.

---

## env의 역할

이 프로젝트에서 environment는 다음을 담당한다.

- 박스 도착 스트림 관리
- 버퍼(buffer) 관리
- 팔레트 초기화 및 open/close 관리
- 현재 상태를 observation으로 제공
- time step 진행
- 종료 조건 판단

즉, `env/`는 “실험 세계(world)”를 관리하는 계층이다.

---

## 왜 먼저 env를 구현하나

논문 계획에서 핵심 문제는 단순 3D packing이 아니라,

- 박스가 순차적으로 도착하고
- 미래는 모르고
- 버퍼가 있고
- open/close 가능한 팔레트가 있고
- 상위 의사결정과 하위 배치를 분리하는

**online / sequential decision-making pallet loading** 문제다.

따라서 heuristic이나 planner보다 먼저,
이 문제를 담을 수 있는 환경 구조를 만드는 것이 중요하다.

---

## 현재 파일 설명

---

### `box_stream.py`

실험에 사용할 박스 도착 스트림을 생성한다.

현재 구현은 synthetic generator다.

#### 현재 생성하는 값
- `box_id`
- `width`
- `depth`
- `height`
- `weight`
- `region`
- `arrival_time`

#### 현재 가정
- 박스는 한 step에 하나씩 도착
- region은 균등 샘플링
- 크기와 무게는 난수로 생성
- fragile / category는 아직 기본값만 사용

#### 나중에 확장 가능
- bursty arrival
- 특정 지역 편향
- fragile item 비율 증가
- benchmark / 실제 데이터 로드

---

### `buffer.py`

도착한 박스를 즉시 적재하지 못할 때 임시 보관하는 버퍼를 구현한다.

#### 현재 제공 기능
- `push(box)`
- `pop_first()`
- `remove_by_id(box_id)`
- `snapshot()`
- `is_full()`
- `is_empty()`

#### 현재 특징
- 단순 리스트 기반
- FIFO 스타일
- 용량(capacity) 제한 존재

#### 나중에 확장 가능
- 우선순위 버퍼
- region-aware buffer
- rehandle-aware buffer

---

### `observation.py`

환경 내부 상태(`EnvState`)를 외부 모듈이 읽기 쉬운 observation으로 변환한다.

#### 현재 observation에 포함되는 정보
- `time_step`
- `buffer_size`
- `buffer_box_ids`
- `open_pallets` 요약 정보
- `closed_pallets`
- `processed_boxes`
- `rehandle_count`
- `done`

이 observation은 이후 planner / heuristic / logging 모듈이 활용할 수 있다.

---

### `pallet_env.py`

프로젝트의 메인 환경 클래스 `PalletLoadingEnv`를 정의한다.

#### 현재 주요 메서드
- `reset()`
- `observe()`
- `get_next_arrival()`
- `add_to_buffer()`
- `pop_buffer_first()`
- `remove_from_buffer()`
- `can_open_new_pallet()`
- `open_next_pallet(region)`
- `close_pallet(pallet_id)`
- `mark_processed(box_id)`
- `increment_rehandle()`
- `advance_time()`
- `is_done()`

#### 현재 env가 직접 하지 않는 것
- 실제 pallet 선택
- 실제 3D placement 계산
- support ratio 계산
- 충돌 판정
- LLM parsing

이런 기능은 이후 `planner/`, `heuristic/`, `llm/`에서 담당한다.

---

## 현재 env 설계 원칙

### 1. 환경과 의사결정을 분리
env는 “세계를 관리”하고,
planner/heuristic은 “무엇을 할지 결정”하도록 나눈다.

---

### 2. 재현성 우선
박스 생성은 `config.seed`를 사용하여 동일한 입력 시나리오를 반복 생성할 수 있게 했다.

---

### 3. 확장성 우선
현재는 최소 기능만 구현했지만,
나중에 아래를 추가해도 구조가 크게 흔들리지 않게 설계했다.

- hybrid event mode
- multiple arrivals per step
- richer observation
- rehandle action
- pallet close/open 정책 다양화

---

## 사용 예시

```python
from configs.default_config import EnvConfig
from env.pallet_env import PalletLoadingEnv

config = EnvConfig()
env = PalletLoadingEnv(config)

obs = env.reset()
print("initial observation:", obs)

# 박스 3개 도착 시뮬레이션
for _ in range(3):
    box = env.get_next_arrival()
    print("arrived box:", box)

    if box is not None:
        ok = env.add_to_buffer(box)
        print("buffered:", ok)

    env.advance_time()
    print("current observation:", env.observe())
