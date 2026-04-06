from configs.default_config import EnvConfig
from env.pallet_env import PalletLoadingEnv

from configs.default_config import EnvConfig
from env.pallet_env import PalletLoadingEnv

def choose_action(env, actions):
    """
    간단한 baseline action chooser

    우선순위
    1. assign
    2. 현재 버퍼 박스를 더 이상 못 받는 pallet는 close
    3. open_pallet
    """

    # 1) assign 우선
    for a in actions:
        if a["type"] == "assign":
            return a

    # 2) assign이 없으면 close 후보 검토
    close_candidates = []

    for a in actions:
        if a["type"] != "close_pallet":
            continue

        pallet = env.get_open_pallet_by_id(a["pallet_id"])
        if pallet is None:
            continue

        # 버퍼에 같은 region 박스가 남아 있는지 확인
        same_region_boxes = [
            b for b in env.state.buffer_boxes
            if b.region == pallet.region
        ]

        if not same_region_boxes:
            continue

        # 같은 region 박스 중 가장 낮은 height조차 못 받으면 사실상 full로 간주
        min_box_height = min(b.height for b in same_region_boxes)

        if pallet.used_height + min_box_height > pallet.max_height:
            close_candidates.append((pallet.used_height, a))

    if close_candidates:
        # 더 많이 찬 pallet를 먼저 닫음
        close_candidates.sort(reverse=True, key=lambda x: x[0])
        return close_candidates[0][1]

    # 3) 그 다음 open
    for a in actions:
        if a["type"] == "open_pallet":
            return a

    return None
    
def main():
    config = EnvConfig()
    env = PalletLoadingEnv(config)

    obs = env.reset()
    print("=== initial observation ===")
    print(obs)

    step_idx = 0

    while not env.state.done:
        print(f"\n========== step {step_idx} ==========")

        # 1) 박스 1개 도착
        box = env.get_next_arrival()
        if box is not None:
            ok = env.add_to_buffer(box)
            print("arrived:", box.box_id, "| buffered:", ok)

        # 2) 현재 상태 확인
        print("observation before action:")
        print(env.observe())

        # 3) 가능한 symbolic action 생성
        actions = env.get_feasible_symbolic_actions()
        print("candidate actions:", actions[:10])

        # 4) 간단 baseline 정책
        # assign가 있으면 assign 우선, 없으면 open_pallet, 그것도 없으면 close는 일단 생략
        # 4) baseline action chooser
        chosen_action = choose_action(env, actions)

        if chosen_action is None:
            print("no action selected")
        else:
            print("chosen action:", chosen_action)
            obs, result = env.step(chosen_action)
            print("result:", result)
            print("observation after action:")
            print(obs)

        # 5) 시간 진행
        env.advance_time()

        # 6) done 체크
        print("time advanced ->", env.state.time_step, "| done:", env.state.done)

        step_idx += 1

        # 안전장치
        if step_idx > 200:
            print("stopped by safety break")
            break

    print("\n=== finished ===")
    print("processed boxes:", len(env.state.processed_boxes))
    print("final observation:", env.observe())


if __name__ == "__main__":
    main()