# core

이 폴더는 프로젝트 전반에서 공통으로 사용하는 **핵심 도메인 객체(core domain objects)** 를 정의한다.

여기 들어가는 파일들은 특정 알고리즘에 종속되지 않는다.
즉, heuristic / planner / llm / env가 모두 함께 쓰는 기본 데이터 구조들이다.

---

## 왜 필요한가

논문 실험 코드에서 가장 중요한 것 중 하나는
**도메인 구조를 일관되게 유지하는 것**이다.

예를 들어:

- 박스(Box)는 어떤 속성을 가지는가
- 팔레트(Pallet)는 어떤 상태를 가지는가
- 환경 상태(EnvState)는 어떤 정보로 구성되는가
- 배치 결과(Placement)는 무엇을 저장하는가

이게 흔들리면
환경과 알고리즘 모듈이 서로 다른 형식을 기대하게 되고,
실험 코드가 금방 엉킨다.

따라서 `core/`는 프로젝트 전체의 공통 언어 역할을 한다.

---

## 현재 파일 설명

### `types.py`
공통 데이터 타입을 정의한다.

현재 포함된 타입:

- `Box`
- `Placement`
- `PackedBox`

#### `Box`
아직 적재되지 않은 입력 박스를 표현한다.

주요 필드:
- `box_id`
- `width`
- `depth`
- `height`
- `weight`
- `region`
- `arrival_time`
- `fragile`
- `category`

---

#### `Placement`
박스가 팔레트 위에 실제로 어디에 놓였는지 나타낸다.

주요 필드:
- `x`
- `y`
- `z`
- `w`
- `d`
- `h`
- `rotated`

---

#### `PackedBox`
원본 박스와 배치 결과를 묶은 구조다.

- `box`
- `placement`

팔레트 내부 적재 상태를 기록할 때 사용한다.

---

### `pallet.py`
팔레트 객체를 정의한다.

#### `Pallet`
하나의 팔레트가 어떤 정보를 가지는지 표현한다.

주요 필드:
- `pallet_id`
- `region`
- `width`
- `depth`
- `max_height`
- `max_weight`
- `is_open`
- `packed_boxes`

주요 property:
- `total_weight`
- `used_height`
- `num_boxes`

---

### `state.py`
환경 전체 상태를 나타내는 `EnvState`를 정의한다.

주요 필드:
- `time_step`
- `incoming_boxes`
- `buffer_boxes`
- `open_pallets`
- `closed_pallets`
- `processed_boxes`
- `rehandle_count`
- `done`

---

## 설계 원칙

`core/`에는 다음 성격의 코드만 두는 것이 좋다.

- 도메인 객체
- 상태 표현
- 공통 데이터 타입

반대로 다음은 두지 않는 것이 좋다.

- heuristic 알고리즘
- planner 정책
- LLM 호출 로직
- visualization 코드

그런 로직은 각각 별도 폴더에 둬야 한다.

---

## 사용 예시

```python
from core.types import Box, Placement, PackedBox
from core.pallet import Pallet

box = Box(
    box_id="box_1",
    width=30,
    depth=20,
    height=15,
    weight=8.5,
    region="A",
    arrival_time=0
)

placement = Placement(
    x=0,
    y=0,
    z=0,
    w=30,
    d=20,
    h=15,
    rotated=False
)

packed_box = PackedBox(box=box, placement=placement)

pallet = Pallet(
    pallet_id="pallet_A_1",
    region="A",
    width=110,
    depth=110,
    max_height=200,
    max_weight=1000.0
)

pallet.packed_boxes.append(packed_box)

print(pallet.total_weight)
print(pallet.used_height)