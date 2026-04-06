"""
pallet_env.py

이 파일은 전체 pallet loading environment를 정의한다.

이 environment는 현재 단계에서 다음을 담당한다.

1. 박스 도착 스트림 관리
2. 팔레트 초기화 및 open/close 관리
3. 버퍼 관리
4. 시간 진행(time step advance)
5. 관측값(observation) 제공
6. 종료 조건 판단

중요:
현재 단계의 env는 "환경 정의"에 집중한다.
즉, 실제 박스를 어느 위치에 놓을지(heuristic),
어느 pallet를 선택할지(planner)는 아직 여기서 하지 않는다.

나중에 이런 구조로 연결될 수 있다.

planner -> 어떤 pallet에 보낼지 결정
heuristic -> 해당 pallet 위 어디에 둘지 계산
env -> 실제 상태 업데이트

지금은 그 전 단계로, 시뮬레이션 골격을 먼저 안정적으로 만드는 목적이다.
"""

from typing import List, Optional

from configs.default_config import EnvConfig
from core.pallet import Pallet
from core.state import EnvState
from core.types import Box
from env.box_stream import generate_box_stream
from env.buffer import BoxBuffer
from env.observation import build_observation
from heuristic.placement import try_place_box # V2
from heuristic.support import compute_support_ratio  # V2

class PalletLoadingEnv:
    """
    동적 팔레트 적재 문제를 위한 환경 클래스.

    현재 제공 기능:
    - reset()
    - observe()
    - get_next_arrival()
    - add_to_buffer()
    - pop_buffer_first()
    - open_next_pallet()
    - close_pallet()
    - mark_processed()
    - advance_time()
    - is_done()
    """

    def __init__(self, config: EnvConfig):
        """
        Parameters
        ----------
        config : EnvConfig
            환경 설정 객체
        """
        self.config = config

        # 환경의 현재 상태를 저장하는 객체
        self.state = EnvState()

        # 버퍼 객체
        # 실제 state.buffer_boxes와 동기화해서 사용할 것
        self.buffer = BoxBuffer(capacity=self.config.buffer_capacity)

    def _make_all_pallets(self) -> List[Pallet]:
        """
        전체 팔레트 목록을 생성한다.

        예:
        region_names = ("A", "B")
        pallets_per_region = 2

        이면 다음 팔레트를 생성:
        - pallet_A_1
        - pallet_A_2
        - pallet_B_1
        - pallet_B_2

        Returns
        -------
        List[Pallet]
            생성된 전체 Pallet 리스트
        """
        pallets: List[Pallet] = []

        for region in self.config.region_names:
            for idx in range(self.config.pallets_per_region):
                pallets.append(
                    Pallet(
                        pallet_id=f"pallet_{region}_{idx + 1}",
                        region=region,
                        width=self.config.pallet_width,
                        depth=self.config.pallet_depth,
                        max_height=self.config.pallet_max_height,
                        max_weight=self.config.pallet_max_weight,
                        # 초기에는 닫힌 상태로 두고,
                        # reset()에서 일부만 열어준다.
                        is_open=False,
                    )
                )

        return pallets

    def _initialize_open_and_closed_pallets(
        self, all_pallets: List[Pallet]
    ) -> tuple[List[Pallet], List[Pallet]]:
        """
        reset 시점에 어떤 팔레트를 열고(open),
        어떤 팔레트를 닫아둘지(closed) 결정한다.

        현재 기본 정책:
        - region별로 1개씩 우선 open
        - max_open_pallets 개수 제한을 넘지 않도록 함

        왜 이렇게 하냐?
        - 처음부터 모든 팔레트를 열어두면 open/close 정책 실험 의미가 줄어든다.
        - 너무 복잡한 초기화보다는 단순하고 재현 가능한 기본값이 좋다.

        Parameters
        ----------
        all_pallets : List[Pallet]
            전체 팔레트 목록

        Returns
        -------
        tuple[List[Pallet], List[Pallet]]
            (open_pallets, closed_pallets)
        """
        open_pallets: List[Pallet] = []
        closed_pallets: List[Pallet] = []

        opened_regions = set()

        for pallet in all_pallets:
            # 아직 해당 지역 팔레트를 연 적이 없고,
            # 전체 open 개수 제한도 넘지 않으면 open
            if (
                pallet.region not in opened_regions
                and len(open_pallets) < self.config.max_open_pallets
            ):
                pallet.is_open = True
                open_pallets.append(pallet)
                opened_regions.add(pallet.region)
            else:
                pallet.is_open = False
                closed_pallets.append(pallet)

        return open_pallets, closed_pallets

    def reset(self) -> dict:
        """
        환경을 초기 상태로 리셋한다.

        수행 내용:
        1. 전체 팔레트 생성
        2. 일부 팔레트 open, 나머지 closed
        3. box stream 생성
        4. state 초기화
        5. buffer 초기화

        Returns
        -------
        dict
            초기 observation
        """
        # 전체 팔레트 생성
        all_pallets = self._make_all_pallets()

        # open / closed 분리
        open_pallets, closed_pallets = self._initialize_open_and_closed_pallets(
            all_pallets
        )

        # 박스 도착 스트림 생성
        incoming_boxes = generate_box_stream(self.config)

        # 버퍼 초기화
        self.buffer = BoxBuffer(capacity=self.config.buffer_capacity)

        # state 초기화
        self.state = EnvState(
            time_step=0,
            incoming_boxes=incoming_boxes,
            buffer_boxes=self.buffer.snapshot(),
            open_pallets=open_pallets,
            closed_pallets=closed_pallets,
            finished_pallets=[],
            processed_boxes=[],
            rehandle_count=0,
            done=False,
        )

        return self.observe()

    def _sync_buffer_to_state(self) -> None:
        """
        buffer 객체의 현재 상태를 EnvState.buffer_boxes와 동기화한다.

        왜 필요한가?
        - 실제 버퍼 조작은 BoxBuffer 클래스가 담당
        - observation 등은 EnvState를 읽어감
        - 따라서 buffer와 state를 맞춰주는 과정이 필요하다
        """
        self.state.buffer_boxes = self.buffer.snapshot()

    def observe(self) -> dict:
        """
        현재 환경 상태를 observation 형태로 반환한다.

        Returns
        -------
        dict
            현재 관측값
        """
        self._sync_buffer_to_state()
        return build_observation(self.state)

    def get_next_arrival(self) -> Optional[Box]:
        """
        다음으로 도착할 박스를 하나 꺼낸다.

        현재 구현에서는 incoming_boxes 리스트의 맨 앞 원소를 꺼낸다.

        Returns
        -------
        Optional[Box]
            도착한 박스가 있으면 Box,
            더 이상 없으면 None
        """
        if not self.state.incoming_boxes:
            return None

        return self.state.incoming_boxes.pop(0)

    def add_to_buffer(self, box: Box) -> bool:
        """
        박스를 버퍼에 추가한다.

        Parameters
        ----------
        box : Box
            버퍼에 넣을 박스

        Returns
        -------
        bool
            성공 여부
        """
        success = self.buffer.push(box)
        self._sync_buffer_to_state()
        return success

    def pop_buffer_first(self) -> Optional[Box]:
        """
        버퍼 맨 앞의 박스를 꺼낸다.

        Returns
        -------
        Optional[Box]
            박스가 있으면 반환, 없으면 None
        """
        box = self.buffer.pop_first()
        self._sync_buffer_to_state()
        return box

    def remove_from_buffer(self, box_id: str) -> Optional[Box]:
        """
        특정 box_id를 가진 박스를 버퍼에서 제거한다.

        Parameters
        ----------
        box_id : str
            제거할 박스 ID

        Returns
        -------
        Optional[Box]
            제거된 박스 또는 None
        """
        box = self.buffer.remove_by_id(box_id)
        self._sync_buffer_to_state()
        return box

    def can_open_new_pallet(self) -> bool:
        """
        현재 추가로 팔레트를 열 수 있는지 확인한다.

        Returns
        -------
        bool
            open pallet 수가 max_open_pallets 미만이면 True
        """
        return len(self.state.open_pallets) < self.config.max_open_pallets

    def open_next_pallet(self, region: str) -> Optional[Pallet]:
        """
        특정 region에 해당하는 닫힌 팔레트 하나를 새로 연다.

        Parameters
        ----------
        region : str
            열고 싶은 팔레트의 지역

        Returns
        -------
        Optional[Pallet]
            열기에 성공한 Pallet,
            실패 시 None

        실패하는 경우:
        - 이미 open pallet 수가 제한에 도달함
        - 해당 region의 닫힌 pallet가 더 없음
        """
        # 전체 open 가능 개수 제한 확인
        if not self.can_open_new_pallet():
            return None

        # closed pallet 중 같은 region의 것을 하나 찾아 연다
        for pallet in self.state.closed_pallets:
            if pallet.region == region and not pallet.is_open:
                pallet.is_open = True
                self.state.closed_pallets.remove(pallet)
                self.state.open_pallets.append(pallet)
                return pallet

        return None

    def close_pallet(self, pallet_id: str) -> bool:
        """
        특정 open pallet를 작업 종료 상태로 전환한다.

        Parameters
        ----------
        pallet_id : str
            닫을 팔레트 ID

        Returns
        -------
        bool
            성공 시 True, 실패 시 False
        """
        for pallet in self.state.open_pallets:
            if pallet.pallet_id == pallet_id:
                pallet.is_open = False
                self.state.open_pallets.remove(pallet)
                self.state.finished_pallets.append(pallet)
                return True

        return False
    
    def get_open_pallet_by_id(self, pallet_id: str) -> Optional[Pallet]:  # V2
        for pallet in self.state.open_pallets:
            if pallet.pallet_id == pallet_id:
                    return pallet
        return None


    def get_closed_pallet_by_id(self, pallet_id: str) -> Optional[Pallet]:  # V2
        # 아직 열리지 않은 pallet 중 pallet_id에 해당하는 pallet를 반환함.
        for pallet in self.state.closed_pallets:
            if pallet.pallet_id == pallet_id:
                return pallet
        return None
    
    def get_buffer_box_by_id(self, box_id: str) -> Optional[Box]:  # V2
        # buffer box 찾기 함수 
        for box in self.state.buffer_boxes:
            if box.box_id == box_id:
                return box
        return None

    def mark_processed(self, box_id: str) -> None:
        """
        박스가 처리 완료되었음을 기록한다.

        Parameters
        ----------
        box_id : str
            처리 완료된 박스 ID
        """
        self.state.processed_boxes.append(box_id)

    def increment_rehandle(self) -> None:
        """
        재배치(rehandle) 횟수를 1 증가시킨다.

        현재 단계에서는 planner/heuristic이 실제 rehandle을 수행하지 않지만,
        이후 확장을 고려해 메서드를 미리 둔다.
        """
        self.state.rehandle_count += 1

    def is_done(self) -> bool:
        """
        episode 종료 조건을 검사한다.

        현재 종료 조건:
        - 더 이상 incoming box가 없고
        - buffer도 비어 있으면 종료

        Returns
        -------
        bool
            종료 여부
        """
        return (
            len(self.state.incoming_boxes) == 0
            and len(self.state.buffer_boxes) == 0
        )

    def advance_time(self) -> None:
        """
        환경의 시간을 1 step 진행한다.

        현재 단계에서는 단순히 time_step을 증가시키고,
        done 여부를 다시 계산한다.
        """
        self._sync_buffer_to_state()
        self.state.time_step += 1
        self.state.done = self.is_done()
        
    def execute_planner_action(self, action: dict) -> dict:  # V2
        '''
        planner의 symbolic action을 실제 env 변화로 실행한다.

        action 예시
        ----------
        {"type": "assign", "box_id": "box_3", "pallet_id": "pallet_A_1"}
        {"type": "open_pallet", "region": "A"}
        {"type": "close_pallet", "pallet_id": "pallet_A_1"}
        '''

        action_type = action.get("type")

        if action_type == "assign":
            box_id = action["box_id"]
            pallet_id = action["pallet_id"]

            pallet = self.get_open_pallet_by_id(pallet_id)
            if pallet is None:
                return {"success": False, "reason": "pallet_not_found"}

            box = self.remove_from_buffer(box_id)
            if box is None:
                return {"success": False, "reason": "box_not_in_buffer"}

            success, placement, log = try_place_box(
                config=self.config,
                pallet=pallet,
                box=box,
            )

            if not success:
                # 실패하면 다시 buffer로 되돌려야 함
                self.add_to_buffer(box)
                return {
                    "success": False,
                    "reason": "heuristic_failed",
                    "placement": None,
                    "log": log,
                }

            self.mark_processed(box.box_id)

            return {
                "success": True,
                "reason": "ok",
                "placement": placement,
                "log": log,
                "pallet_id": pallet_id,
                "box_id": box.box_id,
            }

        elif action_type == "open_pallet":
            region = action["region"]
            pallet = self.open_next_pallet(region)

            if pallet is None:
                return {"success": False, "reason": "cannot_open_pallet"}

            return {
                "success": True,
                "reason": "ok",
                "opened_pallet_id": pallet.pallet_id,
            }

        elif action_type == "close_pallet":
            pallet_id = action["pallet_id"]
            ok = self.close_pallet(pallet_id)

            if not ok:
                return {"success": False, "reason": "cannot_close_pallet"}

            return {
                "success": True,
                "reason": "ok",
                "closed_pallet_id": pallet_id,
            }

        else:
            return {"success": False, "reason": "unknown_action_type"}

    def step(self, action: dict) -> tuple[dict, dict]: # V2
        """
        planner action 1개를 실행하고,
        observation과 실행 결과(info)를 반환한다.
        """
        result = self.execute_planner_action(action)
        self._sync_buffer_to_state()
        self.state.done = self.is_done()
        obs = self.observe()
        return obs, result
    
    def get_feasible_symbolic_actions(self) -> list[dict]:
        """
        현재 상태에서 planner가 고려할 수 있는 symbolic action 후보를 생성한다. + 높이 제한 적용 
        아직 heuristic feasibility까지 보장하진 않고,
        1차적인 rule-based pruning만 수행한다.
        """
        self._sync_buffer_to_state()

        actions = []

        # assign 후보
        for box in self.state.buffer_boxes:
            for pallet in self.state.open_pallets:
                # region mismatch는 바로 제외
                if box.region != pallet.region:
                    continue

                # 무게 제한 1차 체크
                if pallet.total_weight + box.weight > pallet.max_weight:
                    continue
                
                # 높이 제한 1차 pruning 
                # 현재 heuristic은 width/depth만 회전하고, height는 그대로이기에
                # box.height 기준으로 잘라도 됨.
                if pallet.used_height + box.height > pallet.max_height:
                    continue
                
                actions.append({
                    "type": "assign",
                    "box_id": box.box_id,
                    "pallet_id": pallet.pallet_id,
                })

        # open pallet 후보
        if self.can_open_new_pallet():
            added_regions = set()
            for pallet in self.state.closed_pallets:
                if pallet.region in added_regions:
                    continue
            
                actions.append({
                    "type": "open_pallet",
                    "region": pallet.region,
                })
                added_regions.add(pallet.region)

        # close pallet 후보
        for pallet in self.state.open_pallets:
            actions.append({
                "type": "close_pallet",
                "pallet_id": pallet.pallet_id,
            })

        return actions
    
    def export_planner_state(self) -> dict:
        """
        PDDL/problem generator가 읽기 좋은 형태로
        현재 env 상태를 추상화해서 반환한다.
        """
        self._sync_buffer_to_state()

        return {
            "time_step": self.state.time_step,
            "buffer_boxes": [
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
                for box in self.state.buffer_boxes
            ],
            "open_pallets": [
                {
                    "pallet_id": pallet.pallet_id,
                    "region": pallet.region,
                    "is_open": pallet.is_open,
                    "total_weight": pallet.total_weight,
                    "used_height": pallet.used_height,
                    "num_boxes": pallet.num_boxes,
                }   
                for pallet in self.state.open_pallets
            ],
            "available_pallets": [
                {
                    "pallet_id": pallet.pallet_id,
                    "region": pallet.region,
                }
                for pallet in self.state.closed_pallets
            ],
            "finished_pallets": [
                {
                    "pallet_id": pallet.pallet_id,
                    "region": pallet.region,
                    "total_weight": pallet.total_weight,
                    "used_height": pallet.used_height,
                    "num_boxes": pallet.num_boxes,
                }
                for pallet in self.state.finished_pallets
            ],
            "processed_boxes": list(self.state.processed_boxes),
            "rehandle_count": self.state.rehandle_count,
            "done": self.state.done,
        }