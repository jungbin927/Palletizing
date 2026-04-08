from configs.default_config import EnvConfig
from env.pallet_env import PalletLoadingEnv

from planner.symbolic_policy import SymbolicPolicy
from planner.external_planner import ExternalPlanner
from planner.plan_parser import PlanParser
from planner.pddl_generator import build_problem_pddl

from core.pddl_heuristic_bridge import (
    ActionBlacklist,
    execute_bridged_action,
)
from heuristic.placement import try_place_box


class SimplePDDLGenerator:
    def __init__(self, env):
        self.env = env

    def generate(self, obs, candidate_actions):
        return build_problem_pddl(self.env.export_planner_state())


def get_box_from_env(env, box_id):
    """
    env 구조 차이를 흡수하기 위한 helper
    """
    # 1) env.boxes
    if hasattr(env, "boxes") and isinstance(env.boxes, dict):
        return env.boxes.get(box_id)

    # 2) env.state.boxes
    if hasattr(env, "state") and hasattr(env.state, "boxes") and isinstance(env.state.boxes, dict):
        return env.state.boxes.get(box_id)

    # 3) env.box_dict
    if hasattr(env, "box_dict") and isinstance(env.box_dict, dict):
        return env.box_dict.get(box_id)

    # 4) env.state.box_dict
    if hasattr(env, "state") and hasattr(env.state, "box_dict") and isinstance(env.state.box_dict, dict):
        return env.state.box_dict.get(box_id)

    # 5) get_box method
    if hasattr(env, "get_box"):
        return env.get_box(box_id)

    return None


def get_pallet_from_env(env, pallet_id):
    """
    env 구조 차이를 흡수하기 위한 helper
    """
    # 1) env.pallets
    if hasattr(env, "pallets") and isinstance(env.pallets, dict):
        return env.pallets.get(pallet_id)

    # 2) env.state.pallets
    if hasattr(env, "state") and hasattr(env.state, "pallets") and isinstance(env.state.pallets, dict):
        return env.state.pallets.get(pallet_id)

    # 3) env.pallet_dict
    if hasattr(env, "pallet_dict") and isinstance(env.pallet_dict, dict):
        return env.pallet_dict.get(pallet_id)

    # 4) env.state.pallet_dict
    if hasattr(env, "state") and hasattr(env.state, "pallet_dict") and isinstance(env.state.pallet_dict, dict):
        return env.state.pallet_dict.get(pallet_id)

    # 5) open / finished pallet 리스트에서 검색
    if hasattr(env, "state"):
        all_pallets = []
        if hasattr(env.state, "open_pallets"):
            all_pallets.extend(env.state.open_pallets)
        if hasattr(env.state, "finished_pallets"):
            all_pallets.extend(env.state.finished_pallets)

        for pallet in all_pallets:
            if getattr(pallet, "pallet_id", None) == pallet_id:
                return pallet

    # 6) get_pallet method
    if hasattr(env, "get_pallet"):
        return env.get_pallet(pallet_id)

    return None


def make_heuristic_adapter(env, config):
    """
    execute_bridged_action()에서 호출할 heuristic adapter.
    여기서는 실험용으로 commit=False를 사용해서
    '미리 배치 가능 여부만' 확인한다.
    """

    def heuristic_place_adapter(action, env_):
        if action.get("type") != "assign":
            return {
                "success": True,
                "placement": None,
                "reason": None,
                "log": {"note": "non-assign action"},
            }

        box_id = action.get("box_id")
        pallet_id = action.get("pallet_id")

        box = get_box_from_env(env_, box_id)
        pallet = get_pallet_from_env(env_, pallet_id)

        if box is None:
            return {
                "success": False,
                "placement": None,
                "reason": "box_not_found",
                "log": {"box_id": box_id},
            }

        if pallet is None:
            return {
                "success": False,
                "placement": None,
                "reason": "pallet_not_found",
                "log": {"pallet_id": pallet_id},
            }

        # 핵심:
        # commit=False 이므로 실제 pallet 상태를 바꾸지 않고
        # feasibility만 체크함
        return try_place_box(
            config=config,
            pallet=pallet,
            box=box,
            commit=False,
        )

    return heuristic_place_adapter


def main():
    config = EnvConfig()
    env = PalletLoadingEnv(config)
    env.reset()

    pddl_generator = SimplePDDLGenerator(env)
    external_planner = ExternalPlanner(
        domain_file_path="domain.pddl",
        docker_image="aibasel/downward",
        search_config="astar(lmcut())",
    )
    plan_parser = PlanParser()

    policy = SymbolicPolicy(
        env=env,
        pddl_generator=pddl_generator,
        external_planner=external_planner,
        plan_parser=plan_parser,
    )

    # 추가: blacklist
    blacklist = ActionBlacklist()

    # 추가: heuristic adapter
    heuristic_adapter = make_heuristic_adapter(env, config)

    step_count = 0
    max_test_steps = 50

    while not env.state.done and step_count < max_test_steps:
        print(f"\n========== STEP {step_count} ==========")

        # 1. 새 박스 도착
        box = env.get_next_arrival()
        if box is not None:
            added = env.add_to_buffer(box)
            print("[ARRIVAL]", box.box_id, box.region, "buffer_added=", added)

        # 2. 현재 observation
        obs = env.observe()
        print("[OBS buffer_size]", obs["buffer_size"])
        print("[OBS processed_box_count]", obs["processed_box_count"])

        # 3. planner action 선택
        action = policy.select_action(obs)
        print("[ACTION]", action)

        # planner가 None을 반환하는 경우 방어
        if action is None:
            print("[INFO] planner returned None action")
            break

        # 4. assign action이면 bridge로 먼저 feasibility check
        if action.get("type") == "assign":
            bridge_result = execute_bridged_action(
                action=action,
                env=env,
                heuristic_place_fn=heuristic_adapter,
                blacklist=blacklist,
            )

            print("[BRIDGE RESULT]", bridge_result)

            if not bridge_result.success:
                print(
                    f"[BRIDGE FAIL] reason={bridge_result.fail_reason}, "
                    f"message={bridge_result.message}"
                )
                print("[BLACKLIST]", blacklist.to_list())
                step_count += 1
                continue

            # bridge 통과 후 기존 env.step 실행
            # (실제 state 반영은 env.step이 담당)
            next_obs, result = env.step(action)
            print("[RESULT]", result)
            print("[NEXT OBS buffer_size]", next_obs["buffer_size"])
            print("[NEXT OBS processed_box_count]", next_obs["processed_box_count"])

        else:
            # assign이 아닌 action은 기존 방식 유지
            next_obs, result = env.step(action)
            print("[RESULT]", result)
            print("[NEXT OBS buffer_size]", next_obs["buffer_size"])
            print("[NEXT OBS processed_box_count]", next_obs["processed_box_count"])

        # 5. 현재 open pallet 상태 요약
        for pallet in env.state.open_pallets:
            print(
                "  [PALLET]",
                pallet.pallet_id,
                "region=", pallet.region,
                "boxes=", pallet.num_boxes,
                "weight=", pallet.total_weight,
                "height=", pallet.used_height,
            )

        step_count += 1

    print("\n========== FINAL ==========")
    print("processed_boxes:", env.state.processed_boxes)
    print("done:", env.state.done)

    print("\n[FINAL PALLETS]")
    for pallet in env.state.open_pallets + env.state.finished_pallets:
        print(
            pallet.pallet_id,
            "region=", pallet.region,
            "boxes=", pallet.num_boxes,
            "weight=", pallet.total_weight,
            "height=", pallet.used_height,
        )

    print("\n[FINAL BLACKLIST]")
    print(blacklist.to_list())


if __name__ == "__main__":
    main()