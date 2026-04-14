from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from llm.openai_client import OpenAIClient


class LLMActionPruner:
    """
    LLM을 이용해 candidate symbolic actions를 pruning하는 모듈.

    역할
    ----
    - env가 만든 feasible symbolic actions를 입력받음
    - 상태(obs) + pallet 요약 + 최근 실패 이력 + action 후보를 LLM에 전달
    - 더 유망한 action subset만 남겨 planner에 반환

    주의
    ----
    - planner를 대체하지 않음
    - 최종 action을 직접 실행하지 않음
    - "후보 action space 축소"만 담당
    """
    
    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        top_k: int = 1,
        temperature: float = 0.0,
    ):
        self.client = OpenAIClient(
            model=model,
            temperature=temperature,
        )
        self.top_k = top_k

    def prune_actions(
        self,
        obs: Dict[str, Any],
        candidate_actions: List[Dict[str, Any]],
        failed_assignments: Optional[List[List[str]]] = None,
    ) -> List[Dict[str, Any]]:
        if not candidate_actions:
            return []

        if len(candidate_actions) <= self.top_k:
            return candidate_actions

        prompt = self._build_prompt(
            obs,
            candidate_actions,
            failed_assignments or [],
        )

        try:
            response_text = self.client.chat(
                system_prompt=(
                    "You are a logistics action pruning module. "
                    "Return JSON only."
                ),
                user_prompt=prompt,
            )

            result = json.loads(response_text)
            keep_indices = result.get("keep_indices", [])

            pruned = [
                candidate_actions[i]
                for i in keep_indices
                if isinstance(i, int) and 0 <= i < len(candidate_actions)
            ]

            if not pruned:
                print("[LLM] fallback original")
                return candidate_actions

            print(f"[LLM] pruned {len(candidate_actions)} -> {len(pruned)}")
            return pruned

        except Exception as e:
            print("[LLM ERROR]", e)
            return candidate_actions

    def _build_prompt(
        self,
        obs: Dict[str, Any],
        actions: List[Dict[str, Any]],
        failed: List[List[str]],
    ) -> str:
        prompt = f"""
Current Observation:

buffer_size: {obs.get("buffer_size")}

open_pallets:
{json.dumps(obs.get("open_pallets", []), indent=2)}

failed_assignments:
{json.dumps(failed, indent=2)}

candidate_actions:
{json.dumps(actions, indent=2)}

Select top {self.top_k} promising actions.

Return JSON only in this format:
{{
  "keep_indices": [0, 1, 2]
}}
"""
        return prompt
    
