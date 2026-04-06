"""
support.py

이 파일은 박스를 특정 (x, y)에 놓았을 때
1) z 높이가 얼마가 되어야 하는지
2) 아래에서 얼마나 지지(support)되고 있는지
를 계산하는 기능을 담당한다.

왜 필요한가?
------------
네 연구는 단순 2D 배치가 아니라 3D pallet loading이다.
즉, 어떤 박스는 바닥(z=0)에 놓이고,
어떤 박스는 다른 박스 위에 올라간다.

따라서 다음이 필요하다.
- 선택한 (x, y) 위치에서 박스 바닥이 닿는 높이 z 계산
- 박스 바닥 면적 중 실제로 아래 물체가 받쳐주는 면적 비율 계산

현재 구현은 "수직 투영 + 바닥면 겹침" 기반의 단순하고 재현 가능한 방식이다.
"""

from typing import List

from core.pallet import Pallet


def overlap_1d(a0: int, a1: int, b0: int, b1: int) -> int:
    """
    1차원 구간 [a0, a1), [b0, b1) 의 겹치는 길이를 계산한다.

    Returns
    -------
    int
        겹치면 양수, 겹치지 않으면 0
    """
    return max(0, min(a1, b1) - max(a0, b0))


def overlap_area_xy(
    ax: int, ay: int, aw: int, ad: int,
    bx: int, by: int, bw: int, bd: int
) -> int:
    """
    두 직사각형의 xy 평면상 겹치는 면적을 계산한다.

    Parameters
    ----------
    a*: 첫 번째 직사각형
    b*: 두 번째 직사각형

    Returns
    -------
    int
        겹치는 면적
    """
    ox = overlap_1d(ax, ax + aw, bx, bx + bw)
    oy = overlap_1d(ay, ay + ad, by, by + bd)
    return ox * oy


def get_support_z(
    pallet: Pallet,
    x: int,
    y: int,
    w: int,
    d: int,
) -> int:
    """
    새로운 박스를 (x, y)에 놓을 때 닿게 되는 z 높이를 계산한다.

    아이디어
    --------
    새로운 박스의 바닥면과 xy 평면상 겹치는 기존 박스들 중,
    가장 높은 top surface(z+h)를 찾는다.
    그 값이 새로운 박스가 놓일 바닥 높이 z가 된다.

    만약 아래에 겹치는 박스가 하나도 없다면 바닥(z=0)에 놓인다.

    Returns
    -------
    int
        해당 위치에서의 지지 바닥 높이
    """
    support_z = 0

    for packed in pallet.packed_boxes:
        p = packed.placement

        # xy 투영이 겹치면, 해당 박스 위에 올라갈 가능성이 있다.
        area = overlap_area_xy(x, y, w, d, p.x, p.y, p.w, p.d)
        if area > 0:
            top_z = p.z + p.h
            if top_z > support_z:
                support_z = top_z

    return support_z


def compute_support_ratio(
    pallet: Pallet,
    x: int,
    y: int,
    z: int,
    w: int,
    d: int,
) -> float:
    """
    새로운 박스가 (x, y, z)에 놓였을 때
    바닥면적 중 얼마나 지지받는지를 계산한다.

    정의
    ----
    support ratio = (아래에서 실제로 받쳐지는 면적) / (박스 바닥 전체 면적)

    구현 규칙
    ---------
    - z == 0 이면 바닥에 직접 놓였으므로 support ratio = 1.0
    - z > 0 이면, top surface가 정확히 z인 기존 박스들만
      "직접 지지하는 물체"로 인정한다
    - 그 박스들과의 xy 겹침 면적 합을 바닥면적으로 나눈다

    주의
    ----
    겹침 면적을 단순 합산하므로, 지지하는 박스들끼리 서로 중첩되는 경우
    면적 이중 계산이 생길 수 있다.
    하지만 일반적인 packing 상태에서는 보통 같은 평면에서 박스끼리 3D 겹침이 없으므로
    초기 버전 heuristic으로는 충분히 괜찮다.
    """
    base_area = w * d

    # 바닥에 놓이면 100% 지지된 것으로 본다.
    if z == 0:
        return 1.0

    supported_area = 0

    for packed in pallet.packed_boxes:
        p = packed.placement

        # 새 박스 바닥(z)을 직접 받치는 물체만 고려
        if p.z + p.h == z:
            supported_area += overlap_area_xy(
                x, y, w, d,
                p.x, p.y, p.w, p.d
            )

    return supported_area / base_area if base_area > 0 else 0.0