### 환경 설정값 정의
### 환경 정의에 필요한 핵심 값들을 먼저 설정

from dataclasses import dataclass


@dataclass
class EnvConfig:
    """
    실험 환경 설정 클래스.

    dataclass를 사용하는 이유:
    - 여러 설정값을 하나의 객체처럼 다룰 수 있음
    - 기본값(default)을 지정하기 쉬움
    - print 했을 때 값 확인이 편함
    - 실험 reproducibility(재현성) 관리에 유리함
    """

    # =========================
    # 1) Pallet physical setting
    # =========================
    # 팔레트의 가로 길이 (x축)
    pallet_width: int = 110
    # 팔레트의 세로 길이 (y축)
    pallet_depth: int = 110
    # 팔레트의 최대 적재 높이 (z축 한계)
    pallet_max_height: int = 200
    # 팔레트가 버틸 수 있는 최대 총 중량
    pallet_max_weight: int = 1000

    # =========================
    # 2) Region / destination setting
    # =========================
    # 총 지역 개수
    num_regions: int = 2
    
    # 지역 이름 목록
    # 예: region A, region B
    region_names: tuple[str, ...] = ("A", "B")

    # =========================
    # 3) Pallet operating policy
    # =========================
    # 동시에 열려 있을 수 있는 팔레트 최대 개수
    # 예: open pallet 2개만 허용
    max_open_pallets_per_region: int = 3
    
    # 지역별 사용할 수 있는 전체 팔레트 개수
    # 예: A 지역 2개, B 지역 2개
    pallets_per_region: int = 10

    # reset 시 각 지역에서 처음 열어둘 팔레트 수
    initial_open_pallets_per_region: int = 2

    # =========================
    # 4) Buffer setting
    # =========================
    # 즉시 적재하지 못한 박스를 임시로 둘 수 있는 버퍼 최대 용량
    buffer_capacity: int = 10

    # =========================
    # 5) Stability-related setting
    # =========================
    # 최소 지지면 비율 기준
    # 예: 0.7이면 박스 바닥 면적의 70% 이상이 아래에서 지지되어야 함
    support_threshold: float = 0.7

    # =========================
    # 6) Rehandle policy
    # =========================
    # 재배치(rehandle) 허용 여부
    allow_rehandle: bool = True

    # 재배치에 부여할 penalty 값
    # 현재 단계에서는 실제 최적화에 직접 사용하지 않을 수 있지만,
    # 이후 planner나 objective function에서 활용할 수 있도록 미리 둔다.
    rehandle_penalty: float = 10.0

    # 버퍼가 가득 차 있으면 재배치 금지할지 여부
    # 실제 운영 가정 반영
    forbid_rehandle_if_buffer_full: bool = True

    # =========================
    # 7) Event / simulation mode
    # =========================
    # 환경 진행 모드
    # "event": 박스가 하나 도착할 때마다 즉시 의사결정
    # "hybrid": 혼잡 시 mini-batch 처리 같은 구조로 나중에 확장 가능
    event_mode: str = "event"

    # 한 episode에서 생성할 총 박스 수
    episode_num_boxes: int = 200
    # 최대 에피소드 수  
    max_steps : int = 1000

    # =========================
    # 8) Random seed
    # =========================
    # 난수 고정용 seed
    # 실험 재현성을 위해 매우 중요
    seed: int = 42