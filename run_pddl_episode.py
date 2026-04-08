# planner/plan_parser.py

from __future__ import annotations


def _restore_box_id(pddl_name: str) -> str:
    # box_32 -> box_32
    return pddl_name.lower()


def _restore_pallet_id(pddl_name: str) -> str:
    # pallet_a_3 -> pallet_A_3
    parts = pddl_name.lower().split("_")
    if len(parts) >= 3 and parts[0] == "pallet":
        return f"pallet_{parts[1].upper()}_{parts[2]}"
    return pddl_name


def parse_plan_text(plan_text: str) -> list[dict]:
    """
    planner 출력 문자열을 action dict 리스트로 변환.

    기대 형식 예:
    (open-new-pallet pallet_b_2 b)
    (assign-box-to-pallet box_32 pallet_b_2 b)
    (close-pallet pallet_a_3)
    """
    actions: list[dict] = []

    for raw_line in plan_text.splitlines():
        line = raw_line.strip().lower()

        if not line:
            continue
        if line.startswith(";"):
            continue
        if line.startswith("time"):
            continue

        line = line.strip("()")
        parts = line.split()

        if not parts:
            continue

        action_name = parts[0]

        if action_name == "open-new-pallet":
            if len(parts) >= 3:
                region = parts[2].upper()
                actions.append({
                    "type": "open_pallet",
                    "region": region,
                })

        elif action_name == "assign-box-to-pallet":
            if len(parts) >= 4:
                box_id = _restore_box_id(parts[1])
                pallet_id = _restore_pallet_id(parts[2])

                actions.append({
                    "type": "assign",
                    "box_id": box_id,
                    "pallet_id": pallet_id,
                })

        elif action_name == "close-pallet":
            if len(parts) >= 2:
                pallet_id = _restore_pallet_id(parts[1])
                actions.append({
                    "type": "close_pallet",
                    "pallet_id": pallet_id,
                })

    return actions