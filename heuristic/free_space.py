"""
free_space.py

이 파일은 팔레트 위에 새로운 박스를 놓기 위해 사용할
후보 위치(candidate positions)를 생성하는 기능을 담당한다.

핵심 아이디어
-------------
3D packing 문제에서 모든 연속 좌표를 다 탐색하는 것은 비현실적이다.
따라서 보통은 "유망한 후보 좌표 집합"만 만든 뒤,
그 좌표들에 대해 feasibility check를 수행한다.

현재 구현은 매우 전형적인 bottom-left style 후보 생성 방식이다.

후보 x, y 생성 규칙
-------------------
1. 항상 원점 (0, 0)을 후보에 포함
2. 이미 적재된 박스들의
   - 오른쪽 끝 x = placed_box.x + placed_box.w
   - 위쪽 끝 y = placed_box.y + placed_box.d
   를 새로운 후보 축으로 사용
3. 이렇게 모은 x 후보와 y 후보의 조합으로 (x, y) 후보를 만든다.

장점
----
- 구현이 간단하고 재현성이 좋다.
- heuristic baseline으로 적절하다.
- 논문 실험 초기 단계에서 충분히 의미 있는 비교가 가능하다.

한계
----
- 최적 배치를 보장하지는 않는다.
- free-space splitting 같은 고급 기법보다 탐색 효율이 낮을 수 있다.
- 향후 extreme point, maximal space, skyline 기반 방식으로 확장 가능하다.
"""

from typing import List, Tuple

from core.pallet import Pallet


def generate_candidate_xy(pallet: Pallet) -> List[Tuple[int, int]]:
    """
    현재 pallet 상태를 기준으로 새로운 박스를 놓을 수 있는
    후보 (x, y) 좌표 리스트를 생성한다.

    Parameters
    ----------
    pallet : Pallet
        현재 적재 상태가 반영된 팔레트 객체

    Returns
    -------
    List[Tuple[int, int]]
        후보 (x, y) 좌표 리스트

    구현 세부
    ---------
    - x 후보와 y 후보를 각각 set으로 모은 뒤 정렬
    - 모든 조합을 만들어 후보로 사용
    - 가장 단순한 bottom-left 탐색 기반
    """

    # 항상 좌측 하단 원점을 후보로 포함
    candidate_x = {0}
    candidate_y = {0}

    # 이미 놓인 박스들의 "경계선"을 새로운 후보 축으로 추가
    for packed in pallet.packed_boxes:
        px = packed.placement.x
        py = packed.placement.y
        pw = packed.placement.w
        pd = packed.placement.d

        # 현재 박스의 오른쪽 끝
        candidate_x.add(px + pw)

        # 현재 박스의 위쪽 끝
        candidate_y.add(py + pd)

    # 정렬된 좌표 후보
    sorted_x = sorted(candidate_x)
    sorted_y = sorted(candidate_y)

    # (x, y) Cartesian product 생성
    candidates = [(x, y) for x in sorted_x for y in sorted_y]

    # x+y가 작은 bottom-left 우선순위를 주기 위해 정렬
    candidates.sort(key=lambda pos: (pos[0] + pos[1], pos[0], pos[1]))

    return candidates