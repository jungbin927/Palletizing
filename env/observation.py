"""
observation.py

이 파일은 현재 environment state를
외부 모듈(planner, heuristic, llm, experiment runner 등)이 읽기 쉬운
observation 형태로 변환하는 역할을 한다.

왜 observation이 필요한가?

환경 내부 상태(EnvState)는 풍부한 정보를 가지고 있지만,
그 자체를 외부에 직접 노출하면:
- 내부 구조에 지나치게 의존하게 되고
- 필요한 정보만 골라 읽기 어렵고
- 나중에 상태 구조를 바꾸기 힘들어진다.

그래서 environment는 내부 상태를 관리하고,
외부에는 "현재 관측 가능한 정보(observation)"를 넘겨주는 방식이 좋다.

현재는 dictionary 형태 observation을 만든다.
나중에는 별도 Observation dataclass로 확장할 수도 있다.
"""

from core.state import EnvState


def build_observation(state: EnvState) -> dict:
    """
    EnvState를 바탕으로 현재 관측값(observation)을 생성한다.

    Parameters
    ----------
    state : EnvState
        현재 환경 상태

    Returns
    -------
    dict
        현재 시점에서 관측 가능한 정보를 정리한 dictionary
    """

    return {
        # 현재 시간 step
        "time_step": state.time_step,

        # 버퍼에 몇 개의 박스가 쌓여 있는지
        "buffer_size": len(state.buffer_boxes),

        # 버퍼 안의 box ID 목록 v2
        "buffer_box_ids": [box.box_id for box in state.buffer_boxes],
        
        "buffer_boxes": [ # box 속성 
        {
            "box_id": box.box_id,
            "region": box.region,
            "weight": box.weight,
            "width": box.width,
            "depth": box.depth,
            "height": box.height,
            "arrival_time": box.arrival_time,
            "fragile": getattr(box, "fragile", False),
            "category": getattr(box, "category", None),
        }
        for box in state.buffer_boxes
    ],

        # 현재 열려 있는 팔레트들의 요약 정보
        "open_pallets": [
            {
                "pallet_id": pallet.pallet_id,
                "region": pallet.region,
                "is_open": pallet.is_open,
                "total_weight": pallet.total_weight,
                "used_height": pallet.used_height,
                "num_boxes": pallet.num_boxes,
                "remaining_weight_capacity": pallet.max_weight - pallet.total_weight, # v2
                "remaining_height_capacity": pallet.max_height - pallet.used_height, # v2
            }
            for pallet in state.open_pallets
        ],

        # 닫혀 있는 팔레트 ID 목록
        "available_pallets": [pallet.pallet_id for pallet in state.closed_pallets],
        "finished_pallets": [pallet.pallet_id for pallet in state.finished_pallets],

        # 지금까지 처리 완료된 박스 수
        "processed_box_count": len(state.processed_boxes),

        # 재배치 횟수
        "rehandle_count": state.rehandle_count,

        # 종료 여부
        "done": state.done,
    }