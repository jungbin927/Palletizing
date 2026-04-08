from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# =========================================================
# 1. Fail reason 표준화
# =========================================================

class FailReason(str, Enum):
    NO_SPACE = "no_space"
    SUPPORT_LOW = "support_low"
    ORIENTATION_FORBIDDEN = "orientation_forbidden"
    HEIGHT_EXCEEDED = "height_exceeded"
    WEIGHT_EXCEEDED = "weight_exceeded"
    REGION_MISMATCH = "region_mismatch"
    PALLET_CLOSED = "pallet_closed"
    UNKNOWN = "unknown"


# =========================================================
# 2. 결과 구조체
# =========================================================

@dataclass
class BridgeResult:
    success: bool
    action: Dict[str, Any]
    fail_reason: Optional[FailReason] = None
    message: str = ""
    placement: Optional[Any] = None
    raw_result: Optional[Dict[str, Any]] = None


# =========================================================
# 3. blacklist 관리
# =========================================================

@dataclass
class ActionBlacklist:
    """
    같은 (box_id, pallet_id) 조합이 반복 실패하는 것을 막기 위한 blacklist.
    """
    blocked_pairs: Set[Tuple[str, str]] = field(default_factory=set)

    def add(self, box_id: str, pallet_id: str) -> None:
        self.blocked_pairs.add((box_id, pallet_id))

    def contains(self, box_id: str, pallet_id: str) -> bool:
        return (box_id, pallet_id) in self.blocked_pairs

    def clear(self) -> None:
        self.blocked_pairs.clear()

    def to_list(self) -> List[Tuple[str, str]]:
        return list(self.blocked_pairs)


# =========================================================
# 4. planner action quick check
# =========================================================

def quick_feasibility_check(action: Dict[str, Any], env) -> Tuple[bool, Optional[FailReason], str]:
    """
    planner action 전에 대략적으로 걸러주는 lightweight check.
    exact geometric feasibility는 heuristic에서 최종 판단한다.

    기대 action 예시:
    {
        "type": "assign",
        "box_id": "box_0",
        "pallet_id": "pallet_a_1",
        "region": "a"
    }
    """

    action_type = action.get("type")

    # assign이 아닌 action은 일단 통과
    if action_type != "assign":
        return True, None, "non-assign action passed"

    box_id = action.get("box_id")
    pallet_id = action.get("pallet_id")

    if box_id is None or pallet_id is None:
        return False, FailReason.UNKNOWN, "box_id or pallet_id missing"

    # env에서 box / pallet 조회하는 함수명이 다를 수 있으므로
    # 프로젝트에 맞게 아래만 수정하면 됨.
    box = _get_box(env, box_id)
    pallet = _get_pallet(env, pallet_id)

    if box is None:
        return False, FailReason.UNKNOWN, f"box not found: {box_id}"

    if pallet is None:
        return False, FailReason.UNKNOWN, f"pallet not found: {pallet_id}"

    # 1) pallet open/closed 상태
    if getattr(pallet, "is_closed", False):
        return False, FailReason.PALLET_CLOSED, f"pallet {pallet_id} is closed"

    # 2) region mismatch
    box_region = getattr(box, "region", None)
    pallet_region = getattr(pallet, "region", None)
    if box_region is not None and pallet_region is not None and box_region != pallet_region:
        return False, FailReason.REGION_MISMATCH, f"box region {box_region} != pallet region {pallet_region}"

    # 3) 높이 rough check
    box_h = getattr(box, "h", None) or getattr(box, "height", None)
    used_height = getattr(pallet, "used_height", 0)
    max_height = getattr(pallet, "max_height", None)

    if box_h is not None and max_height is not None:
        if used_height + box_h > max_height:
            return False, FailReason.HEIGHT_EXCEEDED, (
                f"rough height check failed: {used_height} + {box_h} > {max_height}"
            )

    # 4) 무게 rough check
    box_weight = getattr(box, "weight", None)
    current_weight = getattr(pallet, "current_weight", 0)
    max_weight = getattr(pallet, "max_weight", None)

    if box_weight is not None and max_weight is not None:
        if current_weight + box_weight > max_weight:
            return False, FailReason.WEIGHT_EXCEEDED, (
                f"rough weight check failed: {current_weight} + {box_weight} > {max_weight}"
            )

    # 5) orientation rough rule
    # 예: upright_only 박스는 회전 금지 등
    rotation_allowed = getattr(box, "rotation_allowed", True)
    if rotation_allowed is False and action.get("rotate", False):
        return False, FailReason.ORIENTATION_FORBIDDEN, "rotation is forbidden for this box"

    return True, None, "quick check passed"


# =========================================================
# 5. heuristic result -> fail reason 매핑
# =========================================================

def normalize_heuristic_fail_reason(result: Dict[str, Any]) -> FailReason:
    """
    heuristic_place() 결과를 표준 fail reason으로 변환.
    result 형식은 프로젝트 코드에 맞게 조금씩 수정하면 됨.
    """

    reason = result.get("reason") or result.get("fail_reason") or result.get("message", "")
    reason_str = str(reason).lower()

    if "space" in reason_str:
        return FailReason.NO_SPACE
    if "support" in reason_str or "stability" in reason_str:
        return FailReason.SUPPORT_LOW
    if "orientation" in reason_str or "rotate" in reason_str:
        return FailReason.ORIENTATION_FORBIDDEN
    if "height" in reason_str:
        return FailReason.HEIGHT_EXCEEDED
    if "weight" in reason_str:
        return FailReason.WEIGHT_EXCEEDED
    if "region" in reason_str:
        return FailReason.REGION_MISMATCH
    if "closed" in reason_str:
        return FailReason.PALLET_CLOSED

    return FailReason.UNKNOWN


# =========================================================
# 6. action 실행기
# =========================================================

def execute_bridged_action(
    action: Dict[str, Any],
    env,
    heuristic_place_fn,
    blacklist: ActionBlacklist,
    verbose: bool = True,
) -> BridgeResult:
    """
    planner가 고른 action을
    1) quick check
    2) heuristic / env 실행
    3) 실패 시 blacklist 반영
    순서로 처리한다.
    """

    action_type = action.get("type")

    # -----------------------------------------
    # A. assign action 처리
    # -----------------------------------------
    if action_type == "assign":
        box_id = action.get("box_id")
        pallet_id = action.get("pallet_id")

        if blacklist.contains(box_id, pallet_id):
            return BridgeResult(
                success=False,
                action=action,
                fail_reason=FailReason.UNKNOWN,
                message=f"blacklisted pair: ({box_id}, {pallet_id})",
            )

        ok, fail_reason, msg = quick_feasibility_check(action, env)
        if not ok:
            blacklist.add(box_id, pallet_id)
            return BridgeResult(
                success=False,
                action=action,
                fail_reason=fail_reason,
                message=f"[quick_check_fail] {msg}",
            )

        # heuristic 실행
        result = heuristic_place_fn(action, env)

        # heuristic 결과 형식 가정:
        # {
        #   "success": True/False,
        #   "placement": ...,
        #   "reason": "no feasible space"
        # }
        success = bool(result.get("success", False))

        if success:
            return BridgeResult(
                success=True,
                action=action,
                placement=result.get("placement"),
                message="[heuristic_success]",
                raw_result=result,
            )

        fail_reason = normalize_heuristic_fail_reason(result)
        blacklist.add(box_id, pallet_id)

        return BridgeResult(
            success=False,
            action=action,
            fail_reason=fail_reason,
            message=f"[heuristic_fail] {result.get('reason', 'unknown')}",
            raw_result=result,
        )

    # -----------------------------------------
    # B. open_pallet action 처리
    # -----------------------------------------
    elif action_type == "open_pallet":
        result = env.open_pallet(action["pallet_id"])
        success = bool(result.get("success", False)) if isinstance(result, dict) else bool(result)

        return BridgeResult(
            success=success,
            action=action,
            message="[open_pallet_success]" if success else "[open_pallet_fail]",
            raw_result=result if isinstance(result, dict) else None,
        )

    # -----------------------------------------
    # C. close_pallet action 처리
    # -----------------------------------------
    elif action_type == "close_pallet":
        result = env.close_pallet(action["pallet_id"])
        success = bool(result.get("success", False)) if isinstance(result, dict) else bool(result)

        return BridgeResult(
            success=success,
            action=action,
            message="[close_pallet_success]" if success else "[close_pallet_fail]",
            raw_result=result if isinstance(result, dict) else None,
        )

    # -----------------------------------------
    # D. no-op / 기타
    # -----------------------------------------
    elif action_type == "no_op":
        return BridgeResult(
            success=True,
            action=action,
            message="[no_op]",
        )

    else:
        return BridgeResult(
            success=False,
            action=action,
            fail_reason=FailReason.UNKNOWN,
            message=f"unsupported action type: {action_type}",
        )


# =========================================================
# 7. replanning helper
# =========================================================

def filter_actions_with_blacklist(actions: List[Dict[str, Any]], blacklist: ActionBlacklist) -> List[Dict[str, Any]]:
    """
    planner가 낸 action 목록 중 blacklist에 걸린 assign action 제거
    """
    filtered = []

    for action in actions:
        if action.get("type") != "assign":
            filtered.append(action)
            continue

        box_id = action.get("box_id")
        pallet_id = action.get("pallet_id")

        if not blacklist.contains(box_id, pallet_id):
            filtered.append(action)

    return filtered


def choose_first_valid_action(actions: List[Dict[str, Any]], blacklist: ActionBlacklist) -> Optional[Dict[str, Any]]:
    """
    아주 단순한 baseline chooser.
    blacklist 안 걸린 assign 우선,
    없으면 나머지 action 선택.
    """

    filtered = filter_actions_with_blacklist(actions, blacklist)

    for a in filtered:
        if a.get("type") == "assign":
            return a

    if filtered:
        return filtered[0]

    return None


# =========================================================
# 8. env object 조회 helper
# =========================================================

def _get_box(env, box_id: str):
    """
    프로젝트별로 box 접근 방식이 다를 수 있어서 helper 분리.
    아래 우선순위로 찾아봄.
    """
    if hasattr(env, "boxes") and isinstance(env.boxes, dict):
        return env.boxes.get(box_id)

    if hasattr(env, "box_dict") and isinstance(env.box_dict, dict):
        return env.box_dict.get(box_id)

    if hasattr(env, "get_box"):
        return env.get_box(box_id)

    return None


def _get_pallet(env, pallet_id: str):
    """
    프로젝트별 pallet 접근 방식 helper.
    """
    if hasattr(env, "pallets") and isinstance(env.pallets, dict):
        return env.pallets.get(pallet_id)

    if hasattr(env, "pallet_dict") and isinstance(env.pallet_dict, dict):
        return env.pallet_dict.get(pallet_id)

    if hasattr(env, "get_pallet"):
        return env.get_pallet(pallet_id)

    return None