from configs.default_config import EnvConfig
from env.pallet_env import PalletLoadingEnv

from planner.pddl_generator import build_problem_pddl
from planner.external_planner import ExternalPlanner
from planner.plan_parser import PlanParser


def main():
    # 1) env 생성 및 reset
    config = EnvConfig()
    env = PalletLoadingEnv(config)
    obs = env.reset()

    # 2) 박스 하나 도착시켜서 buffer에 넣기
    first_box = env.get_next_arrival()
    if first_box is None:
        print("No incoming box found.")
        return

    env.add_to_buffer(first_box)

    # 3) 현재 planner_state export
    planner_state = env.export_planner_state()

    print("\n[planner_state]")
    print(planner_state)

    # 4) problem.pddl 텍스트 생성
    problem_text = build_problem_pddl(planner_state)

    print("\n[problem_text]")
    print(problem_text)

    # 5) external planner 준비
    planner = ExternalPlanner(
        domain_file_path="domain.pddl",   # 미리 저장한 domain 파일
        docker_image="aibasel/downward",
        search_config="astar(lmcut())",
    )

    # 6) planner 실행
    result = planner.run(problem_text)

    print("\n[planner result - success]")
    print(result["success"])

    print("\n[planner stdout]")
    print(result["stdout"])

    print("\n[planner stderr]")
    print(result["stderr"])

    # 7) parser로 action 파싱
    parser = PlanParser()
    parsed_actions = parser.parse(result["plan_text"])

    print("\n[parsed actions]")
    print(parsed_actions)


if __name__ == "__main__":
    main()