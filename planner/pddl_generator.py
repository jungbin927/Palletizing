# planner/pddl_generator.py

from __future__ import annotations

from typing import Any


def _sanitize(name: str) -> str:
    """
    PDDL object/action 이름에 안전하게 쓰기 위한 간단한 정리 함수.
    """
    return (
        name.lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def build_domain_pddl() -> str:
    """
    최소 pallet loading용 domain.pddl 문자열 생성.

    현재 범위
    - assign-box-to-pallet
    - open-new-pallet
    - close-pallet

    아직 넣지 않는 것
    - placement 좌표
    - stackable
    - rehandle
    - support/stability
    """
    domain = """
(define (domain pallet_loading)
  (:requirements :strips :typing :negative-preconditions)

  (:types
    box pallet region
  )

  (:predicates
    (arrived ?b - box)
    (box-region ?b - box ?r - region)
    (pallet-region ?p - pallet ?r - region)

    (open ?p - pallet)
    (closed ?p - pallet)

    (assigned ?b - box ?p - pallet)
    (processed ?b - box)
  )

  (:action open-new-pallet
    :parameters (?p - pallet ?r - region)
    :precondition (and
      (closed ?p)
      (pallet-region ?p ?r)
    )
    :effect (and
      (open ?p)
      (not (closed ?p))
    )
  )

  (:action assign-box-to-pallet
    :parameters (?b - box ?p - pallet ?r - region)
    :precondition (and
      (arrived ?b)
      (box-region ?b ?r)
      (pallet-region ?p ?r)
      (open ?p)
      (not (processed ?b))
    )
    :effect (and
      (assigned ?b ?p)
      (processed ?b)
    )
  )

  (:action close-pallet
    :parameters (?p - pallet)
    :precondition (open ?p)
    :effect (and
      (closed ?p)
      (not (open ?p))
    )
  )
)
""".strip()

    return domain


def build_problem_pddl(planner_state: dict[str, Any], problem_name: str = "pallet_problem") -> str:
    """
    export_planner_state() 결과를 받아 problem.pddl 문자열 생성.

    planner_state 예시:
    {
        "time_step": ...,
        "buffer_boxes": [...],
        "open_pallets": [...],
        "available_pallets": [...],
        "finished_pallets": [...],
        "processed_boxes": [...],
        "done": False,
    }
    """
    buffer_boxes = planner_state.get("buffer_boxes", [])
    open_pallets = planner_state.get("open_pallets", [])
    available_pallets = planner_state.get("available_pallets", [])
    finished_pallets = planner_state.get("finished_pallets", [])
    processed_boxes = set(planner_state.get("processed_boxes", []))

    # region 수집
    region_names = sorted(
        {
            _sanitize(box["region"]) for box in buffer_boxes
        }
        | {
            _sanitize(p["region"]) for p in open_pallets
        }
        | {
            _sanitize(p["region"]) for p in available_pallets
        }
        | {
            _sanitize(p["region"]) for p in finished_pallets
        }
    )

    # object 수집
    box_names = [_sanitize(box["box_id"]) for box in buffer_boxes]
    pallet_names = (
        [_sanitize(p["pallet_id"]) for p in open_pallets]
        + [_sanitize(p["pallet_id"]) for p in available_pallets]
        + [_sanitize(p["pallet_id"]) for p in finished_pallets]
    )

    # init 생성
    init_facts: list[str] = []

    # buffer 안에 있는 box는 arrived
    for box in buffer_boxes:
        b = _sanitize(box["box_id"])
        r = _sanitize(box["region"])
        init_facts.append(f"(arrived {b})")
        init_facts.append(f"(box-region {b} {r})")

        if box["box_id"] in processed_boxes:
            init_facts.append(f"(processed {b})")

    # open pallet
    for pallet in open_pallets:
        p = _sanitize(pallet["pallet_id"])
        r = _sanitize(pallet["region"])
        init_facts.append(f"(pallet-region {p} {r})")
        init_facts.append(f"(open {p})")

    # available pallet = closed pallet로 간주
    for pallet in available_pallets:
        p = _sanitize(pallet["pallet_id"])
        r = _sanitize(pallet["region"])
        init_facts.append(f"(pallet-region {p} {r})")
        init_facts.append(f"(closed {p})")

    # finished pallet도 closed로만 기록
    for pallet in finished_pallets:
        p = _sanitize(pallet["pallet_id"])
        r = _sanitize(pallet["region"])
        init_facts.append(f"(pallet-region {p} {r})")
        init_facts.append(f"(closed {p})")

    # goal: 현재 buffer 안의 box들을 모두 processed
    goal_terms = [
        f"(processed {_sanitize(box['box_id'])})"
        for box in buffer_boxes
    ]

    objects_block = []
    if box_names:
        objects_block.append("    " + " ".join(box_names) + " - box")
    if pallet_names:
        objects_block.append("    " + " ".join(pallet_names) + " - pallet")
    if region_names:
        objects_block.append("    " + " ".join(region_names) + " - region")

    objects_str = "\n".join(objects_block) if objects_block else "    ; no objects"
    init_str = "\n    ".join(init_facts) if init_facts else "; no init"
    goal_str = "\n      ".join(goal_terms) if goal_terms else "(and)"

    problem = f"""
(define (problem {problem_name})
  (:domain pallet_loading)

  (:objects
{objects_str}
  )

  (:init
    {init_str}
  )

  (:goal
    (and
      {goal_str}
    )
  )
)
""".strip()

    return problem


def export_pddl_files(planner_state: dict[str, Any], domain_path: str, problem_path: str) -> None:
    """
    domain/problem pddl 파일 저장.
    """
    domain_str = build_domain_pddl()
    problem_str = build_problem_pddl(planner_state)

    with open(domain_path, "w", encoding="utf-8") as f:
        f.write(domain_str)

    with open(problem_path, "w", encoding="utf-8") as f:
        f.write(problem_str)