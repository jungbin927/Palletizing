from typing import Any, Dict, List, Optional


class SymbolicPolicy:
    def __init__(
        self,
        env,
        pddl_generator,
        external_planner,
        plan_parser,
    ):
        self.env = env
        self.pddl_generator = pddl_generator
        self.external_planner = external_planner
        self.plan_parser = plan_parser

    def select_action(
        self,
        obs: Dict[str, Any],
        blacklist: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        blacklist = blacklist or {"failed_assignments": []}

        # 1) feasible symbolic actions
        feasible_actions = self.env.get_feasible_symbolic_actions()

        # 2) blacklist 반영
        filtered_actions = self._filter_blacklist(
            feasible_actions, blacklist
        )

        # 3) 추가 pruning
        candidate_actions = self._prune_actions(
            obs, filtered_actions
        )

        # 4) 후보가 없으면 fallback
        if not candidate_actions:
            return self._fallback_action(obs)

        # 5) PDDL problem 생성
        problem_text = self.pddl_generator.generate(
            obs=obs,
            candidate_actions=candidate_actions,
        )

        # 6) planner 호출
        planner_result = self.external_planner.run(problem_text)

        # 7) planner 실패 시 fallback
        if not planner_result["success"]:
            return self._fallback_action(obs)

        # 8) plan parsing
        parsed_plan = self.plan_parser.parse(
            planner_result["plan_text"]
        )

        # 9) 파싱 결과 없으면 fallback
        if not parsed_plan:
            return self._fallback_action(obs)

        # 10) 첫 action 반환
        selected = parsed_plan[0]

        if selected not in candidate_actions:
            return self._fallback_action(obs)

        return selected

    def _filter_blacklist(
        self,
        actions: List[Dict[str, Any]],
        blacklist: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        failed_pairs = set(
            tuple(x) for x in blacklist.get("failed_assignments", [])
        )

        filtered = []
        for action in actions:
            if action["type"] == "assign":
                pair = (action["box_id"], action["pallet_id"])
                if pair in failed_pairs:
                    continue
            filtered.append(action)
        return filtered

    def _prune_actions(
        self,
        obs: Dict[str, Any],
        actions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        pruned = []

        for action in actions:
            if action["type"] == "assign":
                if not self._basic_assign_check(obs, action):
                    continue
            pruned.append(action)

        return pruned

    def _basic_assign_check(
        self,
        obs: Dict[str, Any],
        action: Dict[str, Any],
    ) -> bool:
        box_id = action["box_id"]
        pallet_id = action["pallet_id"]

        box = self.env.get_box_by_id(box_id)
        pallet = self.env.get_pallet_by_id(pallet_id)
        
        if box is None or pallet is None:
            return False 

        # 1) 닫힌 pallet 제외
        if hasattr(pallet, "is_open") and not pallet.is_open:
            return False

        # 2) region mismatch 제외
        if hasattr(box, "region") and hasattr(pallet, "region"):
            if box.region != pallet.region:
                return False

        # 3) 명백한 max weight 초과 제외
        current_weight = getattr(pallet, "total_weight", 0.0)
        max_weight = getattr(pallet, "max_weight", float("inf"))
        box_weight = getattr(box, "weight", 0.0)

        if current_weight + box_weight > max_weight:
            return False

        return True

    def _fallback_action(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        feasible_actions = self.env.get_feasible_symbolic_actions()

        assign_actions = [
            a for a in feasible_actions
            if a["type"] == "assign"
        ]

        if assign_actions:
            def score(action):
                pallet = self.env.get_pallet_by_id(action["pallet_id"])
                if pallet is None:
                    return float("inf")
                return (
                    getattr(pallet, "num_boxes", 0),
                    getattr(pallet, "used_height", 0),
                    getattr(pallet, "total_weight", 0),
                )

            assign_actions.sort(key=score)
            return assign_actions[0]

        for action in feasible_actions:
            if action["type"] == "open_pallet":
                return action

        for action in feasible_actions:
            if action["type"] == "close_pallet":
                return action

        return {"type": "no_op"}