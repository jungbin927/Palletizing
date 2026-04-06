"""
buffer.py

이 파일은 environment 내부에서 사용하는 박스 버퍼(buffer)를 구현한다.

버퍼는 "도착한 박스를 즉시 적재하지 못했을 때 잠시 보관하는 공간"이다.

논문 문제 정의에서 버퍼는 매우 중요하다.
왜냐하면 online setting에서는 박스가 하나씩 도착하고,
매 시점마다 바로 적재할 수도 있지만,
상황에 따라 잠시 보류하는 선택도 가능해야 하기 때문이다.

예를 들면:
- 같은 지역 팔레트가 아직 꽉 찼음
- 현재 적재하면 안정성이 안 나옴
- 곧 더 적절한 박스와 함께 묶는 게 유리함

이런 경우 박스를 buffer에 넣어둘 수 있다.

현재 단계에서는 아주 단순한 FIFO 스타일 버퍼로 구현한다.
나중에 더 복잡하게 확장 가능하다.
- priority buffer
- region-aware buffer
- rehandle-aware buffer
"""

from typing import List, Optional

from core.types import Box


class BoxBuffer:
    """
    박스를 임시 저장하는 버퍼 클래스.

    현재 기능:
    - 용량(capacity) 관리
    - push(추가)
    - pop_first(맨 앞 박스 꺼내기)
    - snapshot(현재 상태 복사)
    """

    def __init__(self, capacity: int):
        """
        Parameters
        ----------
        capacity : int
            버퍼 최대 용량
        """
        self.capacity = capacity
        self.boxes: List[Box] = []

    def is_full(self) -> bool:
        """
        버퍼가 가득 찼는지 여부를 반환한다.
        """
        return len(self.boxes) >= self.capacity

    def is_empty(self) -> bool:
        """
        버퍼가 비어 있는지 여부를 반환한다.
        """
        return len(self.boxes) == 0

    def push(self, box: Box) -> bool:
        """
        박스를 버퍼에 추가한다.

        Parameters
        ----------
        box : Box
            버퍼에 넣을 박스

        Returns
        -------
        bool
            성공적으로 추가하면 True,
            용량 초과로 실패하면 False
        """
        if self.is_full():
            return False

        self.boxes.append(box)
        return True

    def pop_first(self) -> Optional[Box]:
        """
        버퍼 맨 앞의 박스를 꺼낸다.

        Returns
        -------
        Optional[Box]
            박스가 있으면 Box 반환,
            비어 있으면 None 반환
        """
        if self.is_empty():
            return None

        return self.boxes.pop(0)

    def remove_by_id(self, box_id: str) -> Optional[Box]:
        """
        특정 box_id를 가진 박스를 버퍼에서 제거한다.

        이 기능은 나중에 planner가
        "버퍼에 쌓여 있는 여러 박스 중 특정 박스를 선택"할 때 유용하다.

        Parameters
        ----------
        box_id : str
            제거할 박스의 ID

        Returns
        -------
        Optional[Box]
            제거 성공 시 해당 Box 반환,
            못 찾으면 None 반환
        """
        for idx, box in enumerate(self.boxes):
            if box.box_id == box_id:
                return self.boxes.pop(idx)
        return None

    def snapshot(self) -> List[Box]:
        """
        현재 버퍼 상태를 복사해서 반환한다.

        왜 복사본을 반환하나?
        - 외부 코드가 self.boxes를 직접 수정하지 않게 하기 위해서다.
        """
        return list(self.boxes)

    def __len__(self) -> int:
        """
        len(buffer) 형태로 현재 버퍼 크기를 읽을 수 있게 한다.
        """
        return len(self.boxes)