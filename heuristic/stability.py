"""
stability.py

이 파일은 placement의 안정성 관련 검사를 담당한다.

현재는 다음 3가지를 구현한다.

1. 팔레트 경계 내에 있는지
2. 기존 박스들과 3D 충돌이 없는지
3. 최소 지지면 비율(support ratio threshold)을 만족하는지
4. 단순 하중 견딤(load-bearing) 규칙을 만족하는지

현재 구현은 논문 초기 실험용 baseline 수준으로 의도적으로 단순화했다.
나중에는 다음으로 확장 가능하다.

- center of mass check
- friction / tipping check
- fragile-specific stacking rule
- semantic constraint rule
"""

from core.pallet import Pallet
from core.types import Box


def boxes_intersect_3d(
    ax: int, ay: int, az: int, aw: int, ad: int, ah: int,
    bx: int, by: int, bz: int, bw: int, bd: int, bh: int,
) -> bool:
    """
    두 3D 직육면체가 겹치는지 검사한다.

    반열린 구간 [x, x+w), [y, y+d), [z, z+h) 방식으로 본다.

    Returns
    -------
    bool
        겹치면 True, 아니면 False
    """
    x_overlap = (ax < bx + bw) and (bx < ax + aw)
    y_overlap = (ay < by + bd) and (by < ay + ad)
    z_overlap = (az < bz + bh) and (bz < az + ah)

    return x_overlap and y_overlap and z_overlap


def in_bounds(
    pallet: Pallet,
    x: int,
    y: int,
    z: int,
    w: int,
    d: int,
    h: int,
) -> bool:
    """
    박스가 팔레트 경계를 벗어나지 않는지 검사한다.
    """
    if x < 0 or y < 0 or z < 0:
        return False

    if x + w > pallet.width:
        return False

    if y + d > pallet.depth:
        return False

    if z + h > pallet.max_height:
        return False

    return True


def collides_with_any(
    pallet: Pallet,
    x: int,
    y: int,
    z: int,
    w: int,
    d: int,
    h: int,
) -> bool:
    """
    새로운 박스가 기존 적재 박스들과 3D 충돌하는지 검사한다.
    """
    for packed in pallet.packed_boxes:
        p = packed.placement
        if boxes_intersect_3d(
            x, y, z, w, d, h,
            p.x, p.y, p.z, p.w, p.d, p.h
        ):
            return True
    return False


def check_load_bearing_simple(
    pallet: Pallet,
    box: Box,
    x: int,
    y: int,
    z: int,
    w: int,
    d: int,
) -> bool:
    """
    단순 하중 견딤 규칙 검사.

    현재 매우 단순한 surrogate rule:
    - 새 박스가 z>0이면, 아래에서 직접 받치는 박스들의 weight보다
      너무 과도하게 무거운 박스는 막는다.
    - 현재는 아래 박스 하나하나의 max load를 따로 모델링하지 않으므로,
      "너무 무거운 박스가 작은 박스 위에 올라가는 것"을 거칠게 제한하는 용도다.

    구현 규칙(초기 버전)
    ---------------------
    - z == 0 이면 바닥 적재이므로 True
    - z > 0 이면, 바로 아래(top surface == z) 에 있는 지지 박스들의 총 무게 합을 계산
    - 새 박스 무게가 그 합의 1.5배를 넘으면 False

    이 규칙은 물리적으로 엄밀한 모델은 아니지만,
    baseline heuristic의 나쁜 적재를 어느 정도 걸러주는 역할을 한다.
    """
    if z == 0:
        return True

    supporting_weight_sum = 0.0

    for packed in pallet.packed_boxes:
        p = packed.placement

        # 새 박스 바닥과 직접 닿는 top surface만 고려
        if p.z + p.h != z:
            continue

        # xy 투영이 겹치는 경우만 지지 후보
        x_overlap = max(0, min(x + w, p.x + p.w) - max(x, p.x))
        y_overlap = max(0, min(y + d, p.y + p.d) - max(y, p.y))
        if x_overlap * y_overlap > 0:
            supporting_weight_sum += packed.box.weight

    # 지지하는 물체가 없는데 공중에 떠 있으면 당연히 불가
    if supporting_weight_sum == 0:
        return False

    # 단순 경험적 제한
    return box.weight <= 1.5 * supporting_weight_sum


def respects_weight_limit(pallet: Pallet, box: Box) -> bool:
    """
    팔레트 최대 하중 제한 검사.
    """
    return (pallet.total_weight + box.weight) <= pallet.max_weight