# heuristic

이 폴더는 **저수준 기하 배치(low-level geometric packing)** 를 담당한다.

논문 전체 구조에서 heuristic module의 역할은 다음과 같다.

- 박스를 실제로 어디에 놓을지 `(x, y, z)` 계산
- 어떤 orientation으로 놓을지 결정
- 충돌 여부 검사
- 지지면 비율 계산
- 안정성 제약 검사
- feasible placement 중 휴리스틱 기준으로 하나 선택

즉, planner가 “어느 pallet에 보낼지”를 정한다면,
heuristic은 “그 pallet 안의 어디에 어떻게 놓을지”를 정하는 계층이다.

---

## 현재 파일 설명

### `free_space.py`
후보 `(x, y)` 좌표를 생성한다.

현재는 가장 단순한 bottom-left 계열 방식이다.

#### 핵심 아이디어
- `(0,0)`은 항상 후보
- 기존 박스들의 오른쪽 끝, 위쪽 끝을 새로운 후보 축으로 사용
- 후보 x, y의 조합을 모두 만들고 bottom-left 우선순위로 정렬

---

### `support.py`
박스를 특정 `(x, y)`에 놓았을 때

- 실제 바닥 높이 `z`
- support ratio

를 계산한다.

#### 포함 기능
- `overlap_1d`
- `overlap_area_xy`
- `get_support_z`
- `compute_support_ratio`

---

### `stability.py`
placement의 기본 제약을 검사한다.

#### 현재 포함된 검사
- 팔레트 경계 내 여부
- 기존 박스와의 3D 충돌 여부
- 팔레트 최대 하중 초과 여부
- support ratio threshold 만족 여부
- 단순 load-bearing 규칙

#### 현재 한계
아직 물리적으로 엄밀한 안정성 모델은 아니다.
초기 baseline용 surrogate model이다.

---

### `placement.py`
heuristic module의 핵심 파일이다.

#### 현재 포함 기능
- orientation 후보 생성
- candidate `(x, y)` 탐색
- `z` 계산
- feasibility check
- heuristic score 계산
- 최적 placement 선택
- pallet 상태에 실제 반영

#### 현재 heuristic score
```python
(z, x + y, x, y)