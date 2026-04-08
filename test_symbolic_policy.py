from configs.default_config import EnvConfig
from env.pallet_env import PalletLoadingEnv

from planner.symbolic_policy import SymbolicPolicy
from planner.external_planner import ExternalPlanner
from planner.plan_parser import PlanParser
from planner.pddl_generator import build_problem_pddl


class SimplePDDLGenerator:
    def generate(self, obs, candidate_actions):
        # 현재는 obs/candidate_actions를 직접 쓰지 않고
        # env.export_planner_state() 기반 problem 생성만 확인하는 테스트용 wrapper
        # SymbolicPolicy 인터페이스 맞추기 위한 최소 어댑터
        return build_problem_pddl(env.export_planner_state())


def main():
    global env

    config = EnvConfig()
    env = PalletLoadingEnv(config)
    env.reset()

    # box 하나 buffer에 넣기
    box = env.get_next_arrival()
    if box is None:
        print("No box arrived.")
        return

    env.add_to_buffer(box)

    obs = env.observe()

    pddl_generator = SimplePDDLGenerator()

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

    action = policy.select_action(obs)

    print("\n[selected action]")
    print(action)


if __name__ == "__main__":
    main()