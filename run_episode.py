# run_episode.py

from env.pallet_env import PalletLoadingEnv
from configs.default_config import EnvConfig

from planner.symbolic_policy import SymbolicPolicy
from planner.external_planner import ExternalPlanner
from planner.plan_parser import PlanParser
from planner.planner_state_exporter import export_planner_state
from planner.pddl_generator import build_problem_pddl

from bridge.placement_adapter import PlacementAdapter
from bridge.execution_monitor import ExecutionMonitor

# from replanning.replanning_manager import ReplanningManager

from heuristic.placement import try_place_box


def run_episode():

    # ---------------------------
    # 1️⃣ 환경 생성
    # ---------------------------

    config = EnvConfig()
    env = PalletLoadingEnv(config)

    obs = env.observe()

    # ---------------------------
    # 2️⃣ planner 관련 모듈 생성
    # ---------------------------
    planner_state = export_planner_state(env)
    problem_text = build_problem_pddl(planner_state)

    external_planner = ExternalPlanner(
        domain_file_path="domain.pddl"
    )

    plan_parser = PlanParser()

    symbolic_policy = SymbolicPolicy(
        env=env,
        pddl_generator=problem_text,
        external_planner=external_planner,
        plan_parser=plan_parser,
    )

    # ---------------------------
    # 3️⃣ bridge / monitor 생성
    # ---------------------------

    adapter = PlacementAdapter()
    monitor = ExecutionMonitor()
    # replanner = ReplanningManager()

    # ---------------------------
    # 4️⃣ Episode Loop 시작
    # ---------------------------

    done = False
    step_count = 0

    while not done:

        obs = env.observe()

        retry_count = 0
        executed = False

        while not executed:

            # -------------------
            # symbolic planning
            # -------------------

            symbolic_action = symbolic_policy.select_action(
                obs,
                # blacklist=replanner.build_blacklist()
            )

            # -------------------
            # symbolic → placement
            # -------------------

            bridged_action = adapter.convert_action(
                symbolic_action,
                env
            )

            # -------------------
            # 실행
            # -------------------

            if bridged_action["type"] == "place_box":

                success, placement, log = try_place_box(
                    config=config,
                    pallet=bridged_action["pallet"],
                    box=bridged_action["box"],
                )
                
                if success:
                    result = {
                        "success": True,
                         "position": (placement.x, placement.y, placement.z),
                         "orientation": (placement.w, placement.d, placement.h),
                        "placement": placement,
                        "support_ratio": log.get("best_support_ratio"),
                         "reason": "ok",
                        "log": log,
                    }
                else:
                    result = {
                        "success": False,
                        "position": None,
                        "orientation": None,
                        "placement": None,
                        "support_ratio": None,
                        "reason": "no_feasible_placement",
                        "log": log,
                    }

            # -------------------
            # 결과 기록
            # -------------------

            monitor.record(
                symbolic_action,
                result
            )

            # -------------------
            # 성공 처리
            # -------------------

            if result["success"]:
                # try_place_box가 이미 pallet 상태를 반영함
                # 여기서는 env bookkeeping만 필요하면 추가
                executed = True

                

            # -------------------
            # 실패 처리
            # -------------------
            """
            else:

                replanner.register_failure(
                    symbolic_action,
                    result.get("reason")
                )

                retry_count += 1

                if not replanner.should_retry(
                    retry_count
                ):
                    executed = True
            """
        done = env.is_done()

        step_count += 1

    print("Episode finished")
    print("Total steps:", step_count)


if __name__ == "__main__":
    run_episode()