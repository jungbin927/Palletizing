"""
box_stream.py

이 파일은 실험에서 사용할 박스 도착 스트림(box stream)을 생성한다.

이 프로젝트의 문제 정의는 "박스가 순차적으로 도착하는 online / dynamic pallet loading"
문제이므로, 한 번에 모든 박스를 단순 리스트로 다루는 것이 아니라
"시간 순서에 따라 도착하는 박스 목록"을 생성하는 것이 중요하다.

현재 단계에서는 synthetic generator(인공 생성기)로 박스를 만든다.
즉, 실제 물류 데이터가 아니라 난수 기반으로 박스 크기, 무게, 지역 등을 샘플링한다.

왜 이렇게 시작하나?
- 초기 구현이 빠름
- 실험 재현성이 좋음
- seed를 고정하면 동일한 입력 시나리오를 반복 생성 가능
- 이후 benchmark 데이터나 실제 데이터로 교체하기 쉬움

나중에는 이 파일을 확장해서 다음도 가능하다.
- bursty arrival pattern
- region imbalance
- fragile / category 분포 제어
- 실제 CSV/JSON 파일 로드
"""

import random
from typing import List

from core.types import Box
from configs.default_config import EnvConfig


def generate_box_stream(config: EnvConfig) -> List[Box]:
    """
    실험용 박스 도착 스트림을 생성한다.

    Parameters
    ----------
    config : EnvConfig
        실험 환경 설정 객체.
        episode_num_boxes, region_names, seed 등의 값을 사용한다.

    Returns
    -------
    List[Box]
        arrival_time 순으로 정렬된 Box 객체 리스트.

    구현 방식
    ----------
    - 현재는 간단한 synthetic generator
    - 매 time step마다 박스 하나가 도착한다고 가정
    - 박스의 width/depth/height/weight/region을 난수로 생성
    - fragile, category는 현재는 기본값만 사용
    """

    # Python의 독립적인 random generator를 사용한다.
    # 전역 random.seed()를 직접 바꾸지 않고 local RNG를 쓰면
    # 다른 코드와의 간섭이 줄어든다.
    rng = random.Random(config.seed)

    boxes: List[Box] = []

    # 한 episode에서 생성할 전체 박스 수만큼 반복
    for t in range(config.episode_num_boxes):
        # 현재는 지역을 균등 확률로 선택
        region = rng.choice(config.region_names)

        # 박스 크기 샘플링
        # 단위는 현재 정수로 두었고, cm라고 생각하면 된다.
        width = rng.randint(20, 50)
        depth = rng.randint(20, 50)
        height = rng.randint(10, 40)

        # 박스 무게 샘플링
        # 소수점 둘째 자리까지 반올림
        weight = rng.randint(5, 20)

        # Box 객체 생성
        box = Box(
            box_id=f"box_{t}",
            width=width,
            depth=depth,
            height=height,
            weight=weight,
            region=region,
            arrival_time=t,
            fragile=False,
            category=None,
        )

        boxes.append(box)

    # 현재는 arrival_time이 생성 순서와 같으므로 사실상 이미 정렬되어 있다.
    # 그래도 명시적으로 정렬해두면 나중에 generator를 바꿔도 안전하다.
    boxes.sort(key=lambda b: b.arrival_time)

    return boxes