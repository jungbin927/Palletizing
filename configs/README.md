## 현재 파일

### `default_config.py`
기본 실험 환경 설정을 담고 있는 파일이다.

현재 정의한 주요 설정은 다음과 같다.

### 1. Pallet physical setting
- `pallet_width`
- `pallet_depth`
- `pallet_max_height`
- `pallet_max_weight`

팔레트의 물리적 크기와 최대 하중을 정의한다.

---

### 2. Region / destination setting
- `num_regions`
- `region_names`

배송 지역 또는 목적지 범주를 정의한다.

---

### 3. Pallet operating policy
- `max_open_pallets`
- `pallets_per_region`

동시에 몇 개의 팔레트를 열 수 있는지,
지역별로 몇 개의 팔레트를 운용할 수 있는지 정의한다.

---

### 4. Buffer setting
- `buffer_capacity`

즉시 적재하지 못한 박스를 임시 보관할 수 있는 버퍼 크기다.

---

### 5. Stability-related setting
- `support_threshold`

최소 지지면 비율 기준이다.
예를 들어 `0.7`이면, 박스 바닥 면적의 70% 이상이 아래에서 지지되어야 한다는 뜻이다.

---

### 6. Rehandle policy
- `allow_rehandle`
- `rehandle_penalty`
- `forbid_rehandle_if_buffer_full`

재배치 허용 여부와 penalty 관련 설정이다.

---

### 7. Event / simulation mode
- `event_mode`
- `episode_num_boxes`

환경이 어떤 방식으로 진행되는지와
한 에피소드에서 처리할 박스 수를 정의한다.

---

### 8. Random seed
- `seed`

실험 재현성을 위한 난수 고정값이다.

---

## 사용 예시

```python
from configs.default_config import EnvConfig

config = EnvConfig()
print(config.pallet_width)
print(config.buffer_capacity)