"""
placement.py

이 파일은 heuristic module의 핵심이다.

역할
----
- 특정 Box를 특정 Pallet에 놓을 수 있는지 탐색
- 회전 여부를 고려
- 후보 (x, y)를 생성
- support z를 계산
- 각종 제약을 검사
- feasible placement 중 가장 좋은 것 하나를 선택
- 실제 pallet 상태에 반영

현재 heuristic 전략
------------------
가장 단순한 bottom-left / lowest-height 계열 scoring 사용:

score = (z, x + y, x, y)

의미:
1. 낮은 z를 우선
2. 더 좌하단에 가까운 위치를 우선
3. x, y가 작은 배치를 선호

이건 초기 baseline으로 매우 자주 쓰이는 형태다.
나중에 stability-aware score, load-aware score, semantic-aware score로 확장 가능하다.
"""

from typing import List, Optional, Tuple

from configs.default_config import EnvConfig
from core.pallet import Pallet
from core.types import Box, Placement, PackedBox
from heuristic.free_space import generate_candidate_xy
from heuristic.support import get_support_z, compute_support_ratio
from heuristic.stability import (
    in_bounds,
    collides_with_any,
    check_load_bearing_simple,
    respects_weight_limit,
)


def get_allowed_orientations(box: Box) -> List[Tuple[int, int, int, bool]]:
    """
    박스가 가질 수 있는 orientation 후보를 반환한다.

    현재는 가장 단순하게:
    - 회전 안 함: (width, depth, height)
    - 바닥면에서 90도 회전: (depth, width, height)

    만 지원한다.

    Returns
    -------
    List[Tuple[int, int, int, bool]]
        (w, d, h, rotated) 튜플 리스트
    """
    
    if hasattr(box, "rotatable") and box.rotatable is False: # v2
        # 일부 카테고리만 회전 허용, LLM 판단 기능을 위한 모듈
        return [(box.width, box.depth, box.height, False)]
    
    orientations = [
        (box.width, box.depth, box.height, False)
    ]
    
    # width와 depth가 다를 때만 회전 후보 추가
    if box.width != box.depth:
        orientations.append((box.depth, box.width, box.height, True))

    return orientations


def heuristic_score(placement: Placement) -> tuple:
    """
    placement의 우선순위를 결정하는 heuristic score.

    낮을수록 더 좋은 배치로 간주한다.
    """
    return (
        placement.z,              # 가능한 낮게 쌓기
        placement.x + placement.y,  # 좌하단 선호
        placement.x,
        placement.y,
    )


def is_valid_placement(
    config: EnvConfig,
    pallet: Pallet,
    box: Box,
    x: int,
    y: int,
    z: int,
    w: int,
    d: int,
    h: int,
) -> tuple[bool, str]:
    """
    해당 위치에 박스를 놓을 수 있는지 검사한다.

    Returns
    -------
    tuple[bool, str]
        (유효 여부, 실패/성공 이유)

    reason 예시
    ----------
    - "ok"
    - "region_mismatch"
    - "weight_limit"
    - "out_of_bounds"
    - "collision"
    - "support_fail"
    - "load_bearing_fail"
    """
    # region mismatch 금지
    if box.region != pallet.region:
        return False, "region_mismatch"

    # 팔레트 최대 하중 제한
    if not respects_weight_limit(pallet, box):
        return False, "weight_limit"

    # 팔레트 경계 / 높이 제한
    if not in_bounds(pallet, x, y, z, w, d, h):
        return False, "out_of_bounds"

    # 기존 박스와 충돌 여부
    if collides_with_any(pallet, x, y, z, w, d, h):
        return False, "collision"

    # 지지면 비율 검사
    support_ratio = compute_support_ratio(pallet, x, y, z, w, d)
    if support_ratio < config.support_threshold:
        return False, "support_fail"

    # 단순 하중 견딤 규칙 검사
    if not check_load_bearing_simple(pallet, box, x, y, z, w, d):
        return False, "load_bearing_fail"

    return True, "ok"


def find_heuristic_placement(
    config: EnvConfig,
    pallet: Pallet,
    box: Box,
) -> tuple[Optional[Placement], dict]:
    """
    주어진 박스를 해당 팔레트에 놓을 수 있는 최적(휴리스틱 기준) placement를 찾는다.

    Returns
    -------
    tuple[Optional[Placement], dict]
        placement가 있으면 Placement, 없으면 None
        두 번째 값은 디버깅/로그용 정보

    log 정보 예시
    -------------
    - tested_candidates
    - feasible_candidates
    - fail_reasons
    """
    best_placement: Optional[Placement] = None
    best_score: Optional[tuple] = None
    best_support_ratio: float = 0.0 # v2
    
    tested_candidates = 0
    feasible_candidates = 0
    fail_reasons: dict[str, int] = {}

    # orientation 후보 순회
    for w, d, h, rotated in get_allowed_orientations(box):
        # xy 후보 생성
        candidate_xy = generate_candidate_xy(pallet)

        for x, y in candidate_xy:
            tested_candidates += 1

            # 현재 (x, y)에서 놓일 바닥 높이 z 계산
            z = get_support_z(pallet, x, y, w, d)

            # placement validity 검사
            valid, reason = is_valid_placement(
                config=config,
                pallet=pallet,
                box=box,
                x=x,
                y=y,
                z=z,
                w=w,
                d=d,
                h=h,
            )

            if not valid:
                fail_reasons[reason] = fail_reasons.get(reason, 0) + 1
                continue

            feasible_candidates += 1

            placement = Placement(
                x=x,
                y=y,
                z=z,
                w=w,
                d=d,
                h=h,
                rotated=rotated,
            )

            support_ratio = compute_support_ratio(pallet, x, y, z, w, d) # v2
            score = heuristic_score(placement)

            if best_placement is None or score < best_score:
                best_placement = placement
                best_support_ratio = support_ratio
                best_score = score

    log = {
        "tested_candidates": tested_candidates,
        "feasible_candidates": feasible_candidates,
        "fail_reasons": fail_reasons,
        "best_support_ratio": best_support_ratio, #v2
    }

    return best_placement, log


def place_box_on_pallet(
    pallet: Pallet,
    box: Box,
    placement: Placement,
) -> None:
    """
    실제로 pallet 상태에 박스를 반영한다.

    Parameters
    ----------
    pallet : Pallet
        대상 팔레트
    box : Box
        적재할 박스
    placement : Placement
        미리 계산된 적재 위치
    """
    pallet.packed_boxes.append(
        PackedBox(
            box=box,
            placement=placement,
        )
    )


def try_place_box(
    config: EnvConfig,
    pallet: Pallet,
    box: Box,
) -> tuple[bool, Optional[Placement], dict]:
    """
    주어진 box를 pallet에 적재 시도하는 편의 함수.

    수행 과정
    --------
    1. placement 탐색
    2. feasible하면 실제 pallet에 반영
    3. 결과 반환

    Returns
    -------
    tuple[bool, Optional[Placement], dict]
        (성공 여부, placement, 로그)
    """
    # 디버깅용 
    print("[DEBUG try_place_box] start", box.box_id, "->", pallet.pallet_id)
    
    placement, log = find_heuristic_placement(config, pallet, box)

    # 디버깅용
    print("[DEBUG try_place_box] placement =", placement)
    print("[DEBUG try_place_box] log =", log)
       
    if placement is None:
        return False, None, log

    place_box_on_pallet(pallet, box, placement)
    return True, placement, log

'''
def _summarize_main_fail_reason(log: dict) -> str:
    """
    fail_reasons에서 가장 많이 나온 실패 원인을 대표 reason으로 반환
    """
    fail_reasons = log.get("fail_reasons", {})
    if not fail_reasons:
        return "unknown"

    return max(fail_reasons.items(), key=lambda x: x[1])[0]


def try_place_box(
    config: EnvConfig,
    pallet: Pallet,
    box: Box,
    commit: bool = True,
) -> tuple[bool, Optional[Placement], dict]:
    """
    주어진 box를 pallet에 적재 시도하는 편의 함수.

    Parameters
    ----------
    commit : bool
        True면 실제 pallet 상태에 반영
        False면 placement만 계산하고 상태는 바꾸지 않음

    Returns
    -------
    tuple[bool, Optional[Placement], dict]
        (성공 여부, placement, log)

    참고
    ----
    기존 코드와의 호환성을 위해 tuple 3개를 반환한다.
    대표 실패 원인은 log["main_reason"]에 추가해둔다.
    """
    print("[DEBUG try_place_box] start", box.box_id, "->", pallet.pallet_id)

    placement, log = find_heuristic_placement(config, pallet, box)

    print("[DEBUG try_place_box] placement =", placement)
    print("[DEBUG try_place_box] log =", log)

    if placement is None:
        log["main_reason"] = _summarize_main_fail_reason(log)
        return False, None, log

    if commit:
        place_box_on_pallet(pallet, box, placement)

    log["main_reason"] = None
    return True, placement, log
'''