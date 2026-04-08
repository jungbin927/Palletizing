from configs.default_config import EnvConfig
from env.pallet_env import PalletLoadingEnv
from planner.pddl_generator import build_domain_pddl, build_problem_pddl
from planner.symbolic_policy import SimpleSymbolicPlanner


def main():
    config = EnvConfig(
        episode_num_boxes=100,
        pallets_per_region=10,
        max_open_pallets_per_region=2,
    )
    env = PalletLoadingEnv(config)
    planner = SimpleSymbolicPlanner()

    obs = env.reset()

    # 초기 도착 몇 개를 buffer에 넣는 예시
    for _ in range(10):
        box = env.get_next_arrival()
        if box is None:
            break
        env.add_to_buffer(box)

    # 현재 상태를 PDDL로 출력
    planner_state = env.export_planner_state()
    domain_str = build_domain_pddl()
    problem_str = build_problem_pddl(planner_state)

    print("===== DOMAIN =====")
    print(domain_str)
    print()
    print("===== PROBLEM =====")
    print(problem_str)
    print()

    # action 하나 뽑아보기
    action = planner.choose_action(env)
    print("chosen action:", action)

    if action is not None:
        next_obs, info = env.step(action)
        print("result:", info)
        print("next processed:", next_obs["processed_box_count"])


if __name__ == "__main__":
    main()