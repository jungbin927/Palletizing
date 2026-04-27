"""
pallet.py

이 파일은 팔레트 객체를 정의한다.

팔레트는 단순한 상자가 아니라,
현재까지 어떤 박스들이 쌓였고,
총 무게가 얼마인지,
현재 사용 높이가 얼마인지 등의 상태를 가지고 있어야 한다.

따라서 Pallet은 environment와 heuristic에서 매우 핵심적인 객체다.
"""

from dataclasses import dataclass, field
from typing import List

from core.types import PackedBox


@dataclass
class Pallet:
    """
    하나의 팔레트를 표현하는 클래스.
    """

    # 팔레트 고유 ID
    # 예: "pallet_A_1"
    pallet_id: str

    # 이 팔레트가 담당하는 지역
    # 예: "A" 또는 "B"
    region: str

    # 팔레트 가로 길이
    width: int
    # 팔레트 세로 길이
    depth: int
    # 최대 허용 높이
    max_height: int
    # 최대 허용 중량
    max_weight: int

    # 현재 열려 있는 팔레트인지 여부
    # open 상태여야 새로운 박스를 배치할 수 있다고 볼 수 있음
    is_open: bool = True

    # 이 팔레트에 적재된 박스 목록
    packed_boxes: List[PackedBox] = field(default_factory=list)

    @property
    def total_weight(self) -> int:
        """
        현재 팔레트에 적재된 전체 박스 무게 합을 반환한다.
        """
        return sum(pb.box.weight for pb in self.packed_boxes)

    @property
    def used_height(self) -> int:
        """
        현재 팔레트에서 사용 중인 최대 높이를 반환한다.

        계산 방식:
        - 적재된 박스가 하나도 없으면 0
        - 박스가 있으면, 각 박스의 (z + h) 중 최대값을 반환
        """
        if not self.packed_boxes:
            return 0

        return max(
            pb.placement.z + pb.placement.h
            for pb in self.packed_boxes
        )

    @property
    def num_boxes(self) -> int:
        """
        현재 적재된 박스 수를 반환한다.
        """
        return len(self.packed_boxes)