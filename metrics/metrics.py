from __future__ import annotations

# dataclass:
# 간단한 데이터 구조를 깔끔하게 정의하기 위해 사용
from dataclasses import dataclass, field

# 타입 힌트를 위한 import
from typing import Dict, Iterable, List


# -----------------------------
# 1. 기본 데이터 구조 정의
# -----------------------------
# metric 계산 시 박스와 팔레트의 정보를
# 일관된 형태로 넣기 위해 dataclass로 정의한다.


@dataclass
class BoxSpec:
    """
    하나의 박스 정보를 저장하는 구조체.

    Attributes
    ----------
    box_id : str
        박스 ID
    width : float
        박스 가로 길이
    depth : float
        박스 세로 길이
    height : float
        박스 높이
    weight : float
        박스 무게 (선택적으로 사용)
    """
    box_id: str
    width: float
    depth: float
    height: float
    weight: float = 0.0


@dataclass
class PalletSpec:
    """
    하나의 팔레트 정보를 저장하는 구조체.

    Attributes
    ----------
    pallet_id : str
        팔레트 ID
    width : float
        팔레트 가로 길이
    depth : float
        팔레트 세로 길이
    max_height : float
        팔레트 최대 높이
    """
    pallet_id: str
    width: float
    depth: float
    max_height: float


@dataclass
class EpisodeMetricsInput:
    """
    한 episode가 끝난 뒤 metric 계산에 필요한 입력값을 모아두는 구조체.

    이 구조체 하나에 episode 전체 정보를 넣고,
    compute_episode_metrics()에 넘기면 주요 지표를 한 번에 계산할 수 있다.

    Attributes
    ----------
    num_arrived : int
        전체 도착한 박스 수
    num_processed : int
        실제 처리 완료된 박스 수
    num_rehandle : int
        재배치(rehandle) 횟수
    num_placement_attempts : int
        전체 배치 시도 횟수
    num_successful_placements : int
        성공한 배치 횟수
    num_stability_fail : int
        안정성 관련 실패 횟수
        예: support_fail, load_bearing_fail
    decision_times : List[float]
        각 step 또는 각 decision의 소요 시간 리스트
    support_ratios : List[float]
        성공한 적재에서의 support ratio 리스트
    used_pallets : List[PalletSpec]
        실제 사용된 팔레트 목록
    packed_boxes : List[BoxSpec]
        실제 적재 완료된 박스 목록
    """
    num_arrived: int
    num_processed: int
    num_rehandle: int = 0
    num_placement_attempts: int = 0
    num_successful_placements: int = 0
    num_stability_fail: int = 0
    decision_times: List[float] = field(default_factory=list)
    support_ratios: List[float] = field(default_factory=list)
    used_pallets: List[PalletSpec] = field(default_factory=list)
    packed_boxes: List[BoxSpec] = field(default_factory=list)


# -----------------------------
# 2. 보조 함수
# -----------------------------
# 박스 부피, 팔레트 부피처럼
# 여러 metric에서 공통으로 쓰이는 기본 계산 함수들이다.


def box_volume(box: BoxSpec) -> float:
    """
    박스 1개의 부피를 계산한다.

    Vol(box) = width * depth * height
    """
    return float(box.width * box.depth * box.height)


def pallet_volume(pallet: PalletSpec) -> float:
    """
    팔레트 1개의 최대 사용 가능 부피를 계산한다.

    Vol(pallet) = width * depth * max_height
    """
    return float(pallet.width * pallet.depth * pallet.max_height)


# -----------------------------
# 3. 개별 metric 계산 함수
# -----------------------------
# 각 함수는 논문에서 쓰일 수 있는 개별 성능 지표를 계산한다.


def throughput(num_processed: int, num_arrived: int) -> float:
    """
    처리율(Throughput)을 계산한다.

    Throughput = processed / arrived

    의미
    ----
    전체 도착한 박스 중 실제 처리 완료된 박스의 비율.
    값이 높을수록 좋다.
    """
    if num_arrived <= 0:
        return 0.0
    return num_processed / num_arrived


def unprocessed_rate(num_processed: int, num_arrived: int) -> float:
    """
    미처리율(Unprocessed Rate)을 계산한다.

    UnprocessedRate = (arrived - processed) / arrived

    의미
    ----
    도착했지만 끝까지 처리되지 못한 박스 비율.
    값이 낮을수록 좋다.
    """
    if num_arrived <= 0:
        return 0.0
    return (num_arrived - num_processed) / num_arrived


def load_factor(
    packed_boxes: Iterable[BoxSpec],
    used_pallets: Iterable[PalletSpec],
) -> float:
    """
    적재 효율(Load Factor)을 계산한다.

    LoadFactor = (적재된 박스 총 부피) / (사용된 팔레트 총 부피)

    의미
    ----
    실제로 사용한 팔레트 공간을 얼마나 효율적으로 채웠는지 나타낸다.
    값이 높을수록 공간 활용이 좋다.
    """
    total_box_volume = sum(box_volume(box) for box in packed_boxes)
    total_pallet_volume = sum(pallet_volume(pallet) for pallet in used_pallets)

    if total_pallet_volume <= 0:
        return 0.0

    return total_box_volume / total_pallet_volume


def pallets_used(used_pallets: Iterable[PalletSpec]) -> int:
    """
    사용된 팔레트 개수를 계산한다.

    의미
    ----
    하나 이상의 박스가 적재된 팔레트 수.
    값이 적을수록 같은 물량을 더 적은 팔레트로 처리한 것이므로 일반적으로 좋다.
    """
    return sum(1 for _ in used_pallets)


def rehandle_rate(num_rehandle: int, num_processed: int) -> float:
    """
    재배치율(Rehandle Rate)을 계산한다.

    RehandleRate = rehandle / processed

    의미
    ----
    박스 1개를 처리하는 데 평균적으로 얼마나 재배치가 발생했는지 나타낸다.
    값이 낮을수록 좋다.
    """
    if num_processed <= 0:
        return 0.0
    return num_rehandle / num_processed


def placement_success_rate(
    num_successful_placements: int,
    num_placement_attempts: int,
) -> float:
    """
    배치 성공률(Placement Success Rate)을 계산한다.

    PlacementSuccessRate = successful_placements / placement_attempts

    의미
    ----
    실제로 배치 시도한 것 중 몇 %가 성공했는지를 나타낸다.
    heuristic + planner 인터페이스 품질을 평가할 때 유용하다.
    """
    if num_placement_attempts <= 0:
        return 0.0
    return num_successful_placements / num_placement_attempts


def stability_failure_rate(
    num_stability_fail: int,
    num_placement_attempts: int,
) -> float:
    """
    안정성 실패율(Stability Failure Rate)을 계산한다.

    StabilityFailureRate = stability_fail / placement_attempts

    의미
    ----
    전체 배치 시도 중 support_fail, load_bearing_fail 같은
    안정성 관련 실패가 얼마나 발생했는지 나타낸다.
    값이 낮을수록 좋다.
    """
    if num_placement_attempts <= 0:
        return 0.0
    return num_stability_fail / num_placement_attempts


def average_decision_time(decision_times: Iterable[float]) -> float:
    """
    평균 의사결정 시간(Average Decision Time)을 계산한다.

    AvgDecisionTime = mean(decision_times)

    의미
    ----
    각 step 또는 각 action 선택에 걸린 평균 시간.
    온라인 의사결정 시스템에서 매우 중요한 운영 지표다.
    값이 낮을수록 좋다.
    """
    decision_times = list(decision_times)
    if not decision_times:
        return 0.0
    return sum(decision_times) / len(decision_times)


def average_support_ratio(support_ratios: Iterable[float]) -> float:
    """
    평균 지지율(Average Support Ratio)을 계산한다.

    AvgSupportRatio = mean(support_ratios)

    의미
    ----
    성공한 적재들에서 평균적으로 어느 정도의 지지면 비율을 확보했는지 나타낸다.
    값이 높을수록 더 안정적인 적재 경향을 보인다.
    """
    support_ratios = list(support_ratios)
    if not support_ratios:
        return 0.0
    return sum(support_ratios) / len(support_ratios)


# -----------------------------
# 4. 통합 metric 계산 함수
# -----------------------------
# 한 episode가 끝난 뒤,
# 필요한 metric들을 한 번에 dictionary 형태로 반환한다.


def compute_episode_metrics(inputs: EpisodeMetricsInput) -> Dict[str, float]:
    """
    한 episode 단위의 주요 성능 지표를 한 번에 계산한다.

    Parameters
    ----------
    inputs : EpisodeMetricsInput
        episode 전체 통계 정보

    Returns
    -------
    Dict[str, float]
        metric 이름과 값이 들어있는 dictionary
    """
    return {
        "throughput": throughput(
            num_processed=inputs.num_processed,
            num_arrived=inputs.num_arrived,
        ),
        "unprocessed_rate": unprocessed_rate(
            num_processed=inputs.num_processed,
            num_arrived=inputs.num_arrived,
        ),
        "load_factor": load_factor(
            packed_boxes=inputs.packed_boxes,
            used_pallets=inputs.used_pallets,
        ),
        "pallets_used": float(
            pallets_used(inputs.used_pallets)
        ),
        "rehandle_rate": rehandle_rate(
            num_rehandle=inputs.num_rehandle,
            num_processed=inputs.num_processed,
        ),
        "placement_success_rate": placement_success_rate(
            num_successful_placements=inputs.num_successful_placements,
            num_placement_attempts=inputs.num_placement_attempts,
        ),
        "stability_failure_rate": stability_failure_rate(
            num_stability_fail=inputs.num_stability_fail,
            num_placement_attempts=inputs.num_placement_attempts,
        ),
        "avg_decision_time": average_decision_time(
            inputs.decision_times
        ),
        "avg_support_ratio": average_support_ratio(
            inputs.support_ratios
        ),
    }