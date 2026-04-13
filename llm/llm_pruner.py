# llm/llm_pruner.py

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from openai import OpenAI


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
        top_k: int = 6,
        temperature: float = 0.0,
        max_failed_pairs_in_prompt: int = 10,
    ):
        self.client = OpenAI()
        self.model = model
        self.top_k = top_k
        self.temperature = temperature
        self.max_failed_pairs_in_prompt = max_failed_pairs_in_prompt

    def prune_actions(
        self,
        obs: Dict[str, Any],
        candidate_actions: List[Dict[str, Any]],
        failed_assignments: Optional[List[List[str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        candidate_actions 중 top-k 유망 action만 남겨 반환.

        Parameters
        ----------
        obs : dict
            현재 observation
        candidate_actions : list[dict]
            env / symbolic policy가 만든 feasible action 후보
        failed_assignments : list[list[str]] | None
            최근 heuristic 실패 pair 리스트
            예: [["box_84", "pallet_A_2"], ["box_89", "pallet_A_2"]]

        Returns
        -------
        list[dict]
            pruning 이후 남긴 action 리스트
        """
        if not candidate_actions:
            return []

        if len(candidate_actions) <= self.top_k:
            return candidate_actions

        prompt = self._build_prompt(
            obs=obs,
            candidate_actions=candidate_actions,
            failed_assignments=failed_assignments or [],
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a logistics planning assistant for dynamic pallet loading. "
                            "Your job is to select the most promising symbolic actions. "
                            "You must return valid JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )

            text = response.choices[0].message.content.strip()
            result = json.loads(text)

            keep_indices = result.get("keep_indices", [])
            keep_indices = [
                idx for idx in keep_indices
                if isinstance(idx, int) and 0 <= idx < len(candidate_actions)
            ]

            # 아무것도 못 고르면 fallback
            if not keep_indices:
                print("[LLM PRUNER] empty keep_indices -> fallback to original candidates")
                return candidate_actions

            # top_k 제한
            keep_indices = keep_indices[: self.top_k]

            pruned = [candidate_actions[idx] for idx in keep_indices]

            print(f"[LLM PRUNER] original={len(candidate_actions)} -> pruned={len(pruned)}")
            return pruned

        except Exception as e:
            print(f"[LLM PRUNER] failed -> fallback to original candidates | error={e}")
            return candidate_actions

    def _build_prompt(
        self,
        obs: Dict[str, Any],
        candidate_actions: List[Dict[str, Any]],
        failed_assignments: List[List[str]],
    ) -> str:
        """
        LLM에 전달할 프롬프트 생성.
        """
        failed_assignments = failed_assignments[: self.max_failed_pairs_in_prompt]

        obs_summary = {
            "buffer_size": obs.get("buffer_size"),
            "processed_box_count": obs.get("processed_box_count"),
            "open_pallets": obs.get("open_pallets", []),
            "buffer_boxes": obs.get("buffer_boxes", []),
        }

        instructions = {
            "goal": (
                "Select the most promising symbolic actions for dynamic pallet loading. "
                "Prefer actions that are more likely to succeed in low-level placement "
                "and improve packing efficiency."
            ),
            "selection_criteria": [
                "Prefer assign actions to pallets with more usable capacity.",
                "Avoid assignments similar to recently failed box-pallet pairs.",
                "Prefer pallets with lower congestion, lower used height, and lower accumulated weight when possible.",
                "Avoid opening a new pallet unless current open pallets are likely saturated or unsuitable.",
                "Prefer close_pallet only when the pallet appears effectively full or repeatedly unsuccessful.",
                "Preserve diversity when useful: do not keep only actions for a single pallet if alternatives look promising.",
            ],
            "required_behavior": [
                f"Select up to {self.top_k} actions.",
                "Indices must refer to the candidate_actions list.",
                "Do not invent new actions.",
                "Return JSON only.",
            ],
            "output_format": {
                "keep_indices": [0, 1, 2],
                "rationale": "brief reason"
            },
        }

        prompt = (
            "Below is the current planning context.\n\n"
            f"OBSERVATION SUMMARY:\n{json.dumps(obs_summary, indent=2, ensure_ascii=False)}\n\n"
            f"RECENT FAILED ASSIGNMENTS:\n{json.dumps(failed_assignments, indent=2, ensure_ascii=False)}\n\n"
            f"CANDIDATE ACTIONS:\n{json.dumps(candidate_actions, indent=2, ensure_ascii=False)}\n\n"
            f"INSTRUCTIONS:\n{json.dumps(instructions, indent=2, ensure_ascii=False)}\n\n"
            "Return a JSON object only."
        )
        return prompt