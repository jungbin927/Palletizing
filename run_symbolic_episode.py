from configs.default_config import EnvConfig
from env.pallet_env import PalletLoadingEnv
from planner.symbolic_policy import SimpleSymbolicPlanner


def run_episode():
    config = EnvConfig(
        episode_num_boxes=100,
        pallets_per_region=20,
        max_open_pallets_per_region=2,
        max_steps=100,
        buffer_capacity=10,
        seed=42,
    )

    env = PalletLoadingEnv(config)
    planner = SimpleSymbolicPlanner()

    obs = env.reset()

    print("=== episode start ===")

    for step_idx in range(config.max_steps):
        if obs["done"]:
            break

        print(f"\n========== step {step_idx} ==========")

        # 1) 새 box arrival
        next_box = env.get_next_arrival()
        if next_box is not None:
            added = env.add_to_buffer(next_box)
            print(f"arrived: {next_box.box_id} | region={next_box.region} | added={added}")
        else:
            print("no new arrival")

        # 2) 현재 상태 확인
        obs = env.observe()
        print("observation before action:")
        print(obs)

        # 3) action 선택
        action = planner.choose_action(env)
        print("chosen action:", action)

        # 4) action 실행
        if action is not None:
            obs, result = env.step(action)
            print("result:", result)
        else:
            print("no action selected")

        # 5) 시간 진행
        env.advance_time()
        obs = env.observe()

        print(
            f"time={obs['time_step']} | processed={obs['processed_boxes']} | "
            f"buffer={obs['buffer_size']} | done={obs['done']}"
        )

    print("\n=== episode finished ===")
    print("final observation:")
    print(obs)
    print("processed boxes:", obs["processed_box_count"])


if __name__ == "__main__":
    run_episode()