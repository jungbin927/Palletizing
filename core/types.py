# 3. `core/types.py`

"""
types.py

이 파일은 프로젝트 전반에서 공통으로 사용하는 핵심 데이터 타입을 정의한다.

현재 단계에서는 다음 3가지를 정의한다.

1. Box
   - 아직 적재되지 않은 입력 박스의 정보

2. Placement
   - 박스가 팔레트 위에 어디에, 어떤 자세로 배치되었는지에 대한 정보

3. PackedBox
   - 실제 박스(Box) + 배치 결과(Placement)를 함께 묶은 객체

이 타입들을 분리해두는 이유:
- env, heuristic, planner가 동일한 타입을 공유할 수 있음
- 데이터 구조가 명확해짐
- 디버깅과 로그 관리가 쉬워짐
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Box:
    """
    아직 적재되지 않은 박스를 표현하는 클래스.

    이 객체는 box stream generator가 생성하며,
    이후 env / planner / heuristic이 공통으로 사용한다.
    """

    # 박스를 구분하기 위한 고유 ID
    box_id: str

    # 박스의 가로 길이 (x 방향)
    width: int

    # 박스의 세로 길이 (y 방향)
    depth: int

    # 박스의 높이 (z 방향)
    height: int

    # 박스 무게
    weight: float

    # 목적지 지역
    # 예: "A", "B"
    region: str

    # 이 박스가 환경에 도착한 시점
    arrival_time: int

    # 깨지기 쉬운 물품인지 여부
    # 현재는 기본값 False로 두고, 나중에 semantic constraint에 활용 가능
    fragile: bool = False

    # 물품 카테고리
    # 예: "detergent", "drink", "electronics"
    # 현재는 optional로 두고 이후 LLM semantic module과 연동 가능
    category: Optional[str] = None


@dataclass
class Placement:
    """
    박스가 팔레트 위에 실제로 놓인 위치와 자세를 표현하는 클래스.

    heuristic module이 placement를 계산하면,
    그 결과를 이 객체로 저장한다.
    """

    # 팔레트 내 x 좌표
    x: int

    # 팔레트 내 y 좌표
    y: int

    # 팔레트 내 z 좌표
    z: int

    # 배치된 상태에서의 가로 길이
    # 회전을 고려하면 원래 Box.width와 달라질 수도 있음
    w: int

    # 배치된 상태에서의 세로 길이
    d: int

    # 배치된 상태에서의 높이
    h: int

    # 회전 여부
    # 예: True이면 width-depth가 바뀌어 들어갔다는 의미로 활용 가능
    rotated: bool = False


@dataclass
class PackedBox:
    """
    실제 박스 정보(Box)와
    그 박스가 어디에 배치되었는지(Placement)를 함께 저장하는 클래스.

    Pallet 객체 내부에서는 packed_boxes 리스트에 PackedBox를 저장한다.
    """

    # 원본 박스 객체
    box: Box

    # 배치 결과
    placement: Placement