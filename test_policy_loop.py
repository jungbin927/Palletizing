from __future__ import annotations

import csv
import time
from pathlib import Path

from configs.default_config import EnvConfig
from env.pallet_env import PalletLoadingEnv

from planner.symbolic_policy import SymbolicPolicy
from planner.external_planner import ExternalPlanner
from planner.plan_parser import PlanParser
from planner.pddl_generator import build_problem_pddl

from visualization.pallet_3d_visualizer import (
    print_env_pallet_summaries,
    save_final_pallet_visualizations,
)

from metrics.metrics import (
    BoxSpec,
    PalletSpec,
    EpisodeMetricsInput,
    compute_episode_metrics,
)

from llm.llm_pruner import LLMActionPruner


class SimplePDDLGenerator:
    def __init__(self, env):
        self.env = env

    def generate(self, obs, candidate_actions):
        return build_problem_pddl(
            planner_state=self.env.export_planner_state(),
            allowed_actions=candidate_actions,
        )


def safe_get(obj, attr_name, default=0):
    return getattr(obj, attr_name, default) if obj is not None else default


def convert_env_box_to_boxspec(box):
    return BoxSpec(
        box_id=safe_get(box, "box_id", "unknown_box"),
        width=float(safe_get(box, "width", safe_get(box, "w", 0.0))),
        depth=float(safe_get(box, "depth", safe_get(box, "d", 0.0))),
        height=float(safe_get(box, "height", safe_get(box, "h", 0.0))),
        weight=float(safe_get(box, "weight", 0.0)),
    )


def append_metrics_to_csv(csv_path: str, row: dict) -> None:
    csv_file = Path(csv_path)
    csv_file.parent.mkdir(parents=True, exist_ok=True)

    file_exists = csv_file.exists()

    with open(csv_file, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def build_episode_metrics(
    env,
    decision_times,
    step_count,
    use_llm_pruning,
    experiment_name,
    num_arrived,
    num_rehandle,
    num_placement_attempts,
    num_successful_placements,
    num_stability_fail,
    support_ratios,
    packed_boxes,
):
    num_processed = len(getattr(env.state, "processed_boxes", []))

    all_pallets = (
        list(getattr(env.state, "open_pallets", [])) +
        list(getattr(env.state, "finished_pallets", []))
    )

    used_pallets = [
        PalletSpec(
            pallet_id=getattr(p, "pallet_id", "unknown_pallet"),
            width=float(getattr(p, "width", getattr(p, "w", 0.0))),
            depth=float(getattr(p, "depth", getattr(p, "d", 0.0))),
            max_height=float(getattr(p, "max_height", 0.0)),
        )
        for p in all_pallets
        if getattr(p, "num_boxes", 0) > 0
    ]

    metric_input = EpisodeMetricsInput(
        num_arrived=num_arrived,
        num_processed=num_processed,
        num_rehandle=num_rehandle,
        num_placement_attempts=num_placement_attempts,
        num_successful_placements=num_successful_placements,
        num_stability_fail=num_stability_fail,
        decision_times=decision_times,
        support_ratios=support_ratios,
        used_pallets=used_pallets,
        packed_boxes=packed_boxes,
    )

    metrics = compute_episode_metrics(metric_input)
    metrics["step_count"] = float(step_count)
    metrics["num_arrived"] = float(num_arrived)
    metrics["num_processed"] = float(num_processed)
    metrics["use_llm_pruning"] = float(1 if use_llm_pruning else 0)
    metrics["experiment_name"] = experiment_name
    return metrics


def print_metrics(metrics: dict) -> None:
    print("\n========== METRICS ==========")
    for k, v in metrics.items():
        print(f"{k}: {v}")


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

    use_llm_pruning = True
    experiment_name = "llm_top1" if use_llm_pruning else "baseline"

    llm_pruner = LLMActionPruner(
        model="gpt-4.1-mini",
        top_k=1,
        temperature=0.0,
    )

    policy = SymbolicPolicy(
        env=env,
        pddl_generator=pddl_generator,
        external_planner=external_planner,
        plan_parser=plan_parser,
        llm_pruner=llm_pruner,
        use_llm_pruning=use_llm_pruning,
    )

    step_count = 0
    max_test_steps = 300
    decision_times = []

    # -------------------------
    # metrics raw stats
    # -------------------------
    num_arrived = 0
    num_rehandle = 0
    num_placement_attempts = 0
    num_successful_placements = 0
    num_stability_fail = 0
    support_ratios = []
    packed_boxes = []
    packed_box_ids = set()

    while not env.state.done and step_count < max_test_steps:
        print(f"\n========== STEP {step_count} ==========")

        # 1) 새 박스 도착
        box = env.get_next_arrival()
        if box is not None:
            num_arrived += 1
            added = env.add_to_buffer(box)
            print("[ARRIVAL]", box.box_id, box.region, "buffer_added=", added)

        # 2) 현재 observation
        obs = env.observe()
        print("[OBS buffer_size]", obs["buffer_size"])
        print("[OBS processed_box_count]", obs["processed_box_count"])

        # 3) policy action 선택 시간 측정
        t0 = time.perf_counter()
        action = policy.select_action(obs)
        t1 = time.perf_counter()

        decision_time = t1 - t0
        decision_times.append(decision_time)

        print("[ACTION]", action)
        print("[DECISION TIME]", decision_time)

        # assign action이면 placement attempt로 기록
        if action.get("type") == "assign":
            num_placement_attempts += 1

        # 4) action 실행
        target_box_obj = None

        if action.get("type") == "assign":
            box_id = action.get("box_id")
            for b in getattr(env.state, "buffer", []):
                if getattr(b, "box_id", None) == box_id:
                    target_box_obj = b
                    break
        
        next_obs, result = env.step(action)
        print("[RESULT]", result)
        print("[NEXT OBS buffer_size]", next_obs["buffer_size"])
        print("[NEXT OBS processed_box_count]", next_obs["processed_box_count"])

        # -------------------------
        # result 기반 metrics 누적
        # -------------------------
        if isinstance(result, dict):
            if action.get("type") == "assign":
                success_flag = bool(result.get("success", False))
                if success_flag:
                    num_successful_placements += 1

                    box_id = action.get("box_id")
                    placement = result.get("placement")

                    if placement is not None and box_id not in packed_box_ids:
                        packed_boxes.append(
                            BoxSpec(
                                box_id=box_id,
                                width=float(getattr(placement, "w", 0.0)),
                                depth=float(getattr(placement, "d", 0.0)),
                                height=float(getattr(placement, "h", 0.0)),
                                weight=float(getattr(target_box_obj, "weight", 0.0)) if target_box_obj is not None else 0.0,
                            )
                        )
                        packed_box_ids.add(box_id)
    
                failure_reason = result.get("reason")
                if failure_reason in ["support_fail", "load_bearing_fail", "stability_fail"]:
                    num_stability_fail += 1

                support_ratio = result.get("support_ratio")
                
                if support_ratio is None:
                    log = result.get("log", {})
                    support_ratio = log.get("best_support_ratio")

                if support_ratio is not None:
                    support_ratios.append(float(support_ratio))

            if result.get("rehandle", False):
                num_rehandle += 1

        # 5) open pallet 상태 요약
        for pallet in env.state.open_pallets:
            print(
                " [PALLET]", pallet.pallet_id,
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

    print_env_pallet_summaries(env)

    save_final_pallet_visualizations(
        env=env,
        step_count=step_count,
        base_dir="experiments",
    )

    
    metrics = build_episode_metrics(
        env=env,
        decision_times=decision_times,
        step_count=step_count,
        use_llm_pruning=use_llm_pruning,
        experiment_name=experiment_name,
        num_arrived=num_arrived,
        num_rehandle=num_rehandle,
        num_placement_attempts=num_placement_attempts,
        num_successful_placements=num_successful_placements,
        num_stability_fail=num_stability_fail,
        support_ratios=support_ratios,
        packed_boxes=packed_boxes,
    )

    print_metrics(metrics)

    append_metrics_to_csv(
        csv_path="experiments/metrics.csv",
        row=metrics,
    )

    print("\n[INFO] metrics saved to experiments/metrics.csv")


if __name__ == "__main__":
    main()