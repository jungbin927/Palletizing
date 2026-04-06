"""
state.py

이 파일은 environment 전체 상태를 표현하는 EnvState를 정의한다.

이 프로젝트는 단순히 "박스 하나를 어디에 둘까?" 문제가 아니라,
시간이 흐르면서 박스가 도착하고,
버퍼에 대기하고,
팔레트가 열리고 닫히는
동적 sequential decision-making 문제다.

따라서 현재 환경 상태를 하나의 객체로 관리하는 것이 중요하다.
"""

from dataclasses import dataclass, field
from typing import List

from core.types import Box
from core.pallet import Pallet


@dataclass
class EnvState:
    """
    환경의 현재 상태를 표현하는 클래스.
    """

    # 현재 time step
    time_step: int = 0

    # 아직 도착하지 않았거나 앞으로 처리할 박스 목록
    # box_stream generator가 만든 리스트를 여기에 저장할 수 있음
    incoming_boxes: List[Box] = field(default_factory=list)

    # 현재 버퍼에 들어 있는 박스 목록
    buffer_boxes: List[Box] = field(default_factory=list)

    # 현재 open 상태인 팔레트 목록
    open_pallets: List[Pallet] = field(default_factory=list)

    # 아직 사용 전이거나 close 상태인 팔레트 목록
    closed_pallets: List[Pallet] = field(default_factory=list)
    
    # 작업 완료 후 닫힌 pallet
    finished_pallets: List[Pallet] = field(default_factory=list)

    # 이미 처리 완료된 박스 ID 목록
    processed_boxes: List[str] = field(default_factory=list)

    # 재배치(rehandle) 수행 횟수
    rehandle_count: int = 0

    # 에피소드 종료 여부
    done: bool = False