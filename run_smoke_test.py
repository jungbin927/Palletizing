from configs.default_config import EnvConfig
from env.pallet_env import PalletLoadingEnv


def choose_action(env, actions, failed_pairs, last_result=None, last_action=None):
    """
    baseline action chooser

    우선순위
    1. 실패 이력이 없는 assign
    2. 직전 assign이 heuristic_failed였다면 close 우선
    3. open_pallet
    """

    # 0) 실패했던 assign pair는 제외
    filtered_actions = []
    for a in actions:
        if a["type"] == "assign":
            pair = (a["box_id"], a["pallet_id"])
            if pair in failed_pairs:
                continue
        filtered_actions.append(a)

    actions = filtered_actions

    # 1) 직전 assign이 heuristic_failed였다면, close를 먼저 고려
    if (
        last_result is not None
        and last_result.get("reason") == "heuristic_failed"
        and last_action is not None
        and last_action.get("type") == "assign"
    ):
        failed_pallet_id = last_action["pallet_id"]

        # 실패한 pallet 먼저 닫기
        for a in actions:
            if a["type"] == "close_pallet" and a["pallet_id"] == failed_pallet_id:
                return a

        # 그 pallet가 없으면 다른 close라도 시도
        for a in actions:
            if a["type"] == "close_pallet":
                return a

        # close가 없으면 open
        for a in actions:
            if a["type"] == "open_pallet":
                return a

    # 2) 일반 상황에서는 assign 우선
    for a in actions:
        if a["type"] == "assign":
            return a

    # 3) assign이 없으면 close 후보 검토
    close_candidates = []

    for a in actions:
        if a["type"] != "close_pallet":
            continue

        pallet = env.get_open_pallet_by_id(a["pallet_id"])
        if pallet is None:
            continue

        same_region_boxes = [
            b for b in env.state.buffer_boxes
            if b.region == pallet.region
        ]

        if not same_region_boxes:
            continue

        # 같은 region 박스 중 가장 낮은 height조차 못 받으면 사실상 full
        min_box_height = min(b.height for b in same_region_boxes)

        if pallet.used_height + min_box_height > pallet.max_height:
            close_candidates.append((pallet.used_height, a))

    if close_candidates:
        close_candidates.sort(reverse=True, key=lambda x: x[0])
        return close_candidates[0][1]

    # 4) 그 다음 open
    for a in actions:
        if a["type"] == "open_pallet":
            return a

    return None


def main():
    config = EnvConfig()
    
    print("episode_num_boxes =", config.episode_num_boxes)
    print("pallets_per_region =", config.pallets_per_region)
    print("region_names =", config.region_names)
    
    env = PalletLoadingEnv(config)

    obs = env.reset()

    print("=== initial observation ===")
    print(obs)
    print("initial open pallets:", [p["pallet_id"] for p in obs["open_pallets"]])
    print("initial available pallets:", obs["available_pallets"])
    print("=== initial observation ===")


    step_idx = 0

    # 실패했던 assign(box, pallet) 기억
    failed_pairs = set()

    # 직전 action / result 기억
    last_action = None
    last_result = None

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

        # 4) baseline action chooser
        chosen_action = choose_action(
            env=env,
            actions=actions,
            failed_pairs=failed_pairs,
            last_result=last_result,
            last_action=last_action,
        )

        if chosen_action is None:
            print("no action selected")
        else:
            print("chosen action:", chosen_action)
            obs, result = env.step(chosen_action)
            print("result:", result)
            print("observation after action:")
            print(obs)

            # assign가 heuristic_failed면 blacklist에 추가
            if (
                chosen_action["type"] == "assign"
                and result.get("reason") == "heuristic_failed"
            ):
                failed_pairs.add(
                    (chosen_action["box_id"], chosen_action["pallet_id"])
                )

            last_action = chosen_action
            last_result = result

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