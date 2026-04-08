# planner/plan_parser.py
# 도커로 띄운 planner가 만든 솔루션, planner stdout을 파싱하여 action하는 역할 

import re
from typing import Dict, List, Optional


class PlanParser:
    def parse(self, planner_output: str) -> List[Dict]:
        actions = []

        for raw_line in planner_output.splitlines():
            line = raw_line.strip().lower()
            if not line:
                continue

            action = self._parse_action_line(line)
            if action:
                actions.append(action)

        return actions

    def _parse_action_line(self, line: str) -> Optional[Dict]:
        # 예:
        # assign-box-to-pallet box_0 pallet_a_1 a (1)
        # open-new-pallet pallet_a_2 a (1)
        # close-pallet pallet_a_1 (1)

        # 뒤에 붙는 "(1)" 같은 cost 제거
        line = re.sub(r"\s+\(\d+\)\s*$", "", line).strip()

        tokens = line.split()
        if not tokens:
            return None

        name = tokens[0]

        if name == "assign-box-to-pallet" and len(tokens) == 4:
            return {
                "type": "assign",
                "box_id": tokens[1],
                "pallet_id": tokens[2],
                "region": tokens[3],
            }

        if name == "open-new-pallet" and len(tokens) == 3:
            return {
                "type": "open_pallet",
                "pallet_id": tokens[1],
                "region": tokens[2],
            }

        if name == "close-pallet" and len(tokens) == 2:
            return {
                "type": "close_pallet",
                "pallet_id": tokens[1],
            }

        # print("[DEBUG parser line]", line)
        # print("[DEBUG parser tokens]", tokens)
        
        return None