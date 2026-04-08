# ExternalPlanner 파이썬에서 단독으로 테스트 

from configs.default_config import EnvConfig
from env.pallet_env import PalletLoadingEnv
from planner.pddl_generator import build_problem_pddl
from planner.external_planner import ExternalPlanner
from planner.plan_parser import PlanParser


def main():
    config = EnvConfig()
    env = PalletLoadingEnv(config)
    env.reset()

    # box 하나 버퍼에 넣기
    box = env.get_next_arrival()
    if box is None:
        print("No box arrived.")
        return

    env.add_to_buffer(box)

    planner_state = env.export_planner_state()
    problem_text = build_problem_pddl(planner_state)

    planner = ExternalPlanner(
        domain_file_path="domain.pddl",
        docker_image="aibasel/downward",
        search_config='astar(lmcut())',
    )

    result = planner.run(problem_text)

    print("\n[success]")
    print(result["success"])

    print("\n[stdout]")
    print(result["stdout"])

    print("\n[stderr]")
    print(result["stderr"])

    parser = PlanParser()
    parsed = parser.parse(result["plan_text"])

    print("\n[parsed actions]")
    print(parsed)


if __name__ == "__main__":
    main()