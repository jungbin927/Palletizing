"""
visualization/pallet_3d_visualizer.py

기능
----
- pallet 위에 적재된 박스들을 3D로 시각화
- 각 박스를 서로 다른 색으로 표시
- box_id 라벨 표시 가능
- pallet별 load factor, box 수, 총 무게, 사용 높이 요약 가능
- env 전체(open / finished pallet)를 순회하며 PNG 저장 가능

사용 예시
---------
from visualization.pallet_3d_visualizer import (
    print_env_pallet_summaries,
    save_env_pallet_visualizations,
)

print_env_pallet_summaries(env)

save_env_pallet_visualizations(
    env=env,
    output_dir="visualization/outputs/test_policy_loop",
    include_open=True,
    include_finished=True,
    annotate_boxes=True,
)
"""

from __future__ import annotations

import os
from typing import Iterable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from datetime import datetime
import os 

# ----------------------------------------
# 기본 계산 함수
# ----------------------------------------

def _box_volume(w: float, d: float, h: float) -> float:
    return float(w * d * h)


def _pallet_volume(width: float, depth: float, max_height: float) -> float:
    return float(width * depth * max_height)


def _compute_pallet_load_factor(pallet) -> float:
    """
    pallet의 적재 효율(load factor) 계산.
    적재된 박스 총 부피 / pallet 전체 부피
    """
    total_box_volume = 0.0

    for packed in pallet.packed_boxes:
        p = packed.placement
        total_box_volume += _box_volume(p.w, p.d, p.h)

    denom = _pallet_volume(pallet.width, pallet.depth, pallet.max_height)
    if denom <= 0:
        return 0.0
    return total_box_volume / denom


def _generate_distinct_colors(n: int):
    """
    박스 개수만큼 서로 다른 색 생성.
    tab20 colormap 기반.
    """
    if n <= 0:
        return []

    cmap = plt.get_cmap("tab20")
    colors = [cmap(i % 20) for i in range(n)]
    return colors


# ----------------------------------------
# 3D cuboid 그리기 관련 함수
# ----------------------------------------

def _cuboid_faces(
    x: float,
    y: float,
    z: float,
    dx: float,
    dy: float,
    dz: float,
) -> List[List[Tuple[float, float, float]]]:
    """
    직육면체의 6개 면(face)을 반환한다.
    """
    # 8개 꼭짓점
    p000 = (x, y, z)
    p100 = (x + dx, y, z)
    p110 = (x + dx, y + dy, z)
    p010 = (x, y + dy, z)

    p001 = (x, y, z + dz)
    p101 = (x + dx, y, z + dz)
    p111 = (x + dx, y + dy, z + dz)
    p011 = (x, y + dy, z + dz)

    faces = [
        [p000, p100, p110, p010],  # bottom
        [p001, p101, p111, p011],  # top
        [p000, p100, p101, p001],  # front
        [p010, p110, p111, p011],  # back
        [p000, p010, p011, p001],  # left
        [p100, p110, p111, p101],  # right
    ]
    return faces


def _draw_pallet_wireframe(ax, pallet):
    """
    pallet 전체 경계를 와이어프레임처럼 그린다.
    """
    faces = _cuboid_faces(
        x=0,
        y=0,
        z=0,
        dx=pallet.width,
        dy=pallet.depth,
        dz=pallet.max_height,
    )

    # 면을 투명하게, 모서리만 연하게 그림
    poly = Poly3DCollection(
        faces,
        facecolors=(0.95, 0.95, 0.95, 0.03),
        edgecolors=(0.3, 0.3, 0.3, 0.25),
        linewidths=0.8,
    )
    ax.add_collection3d(poly)


def _draw_box(ax, packed, color, annotate: bool = True):
    """
    packed box 하나를 3D로 그림.
    """
    box = packed.box
    p = packed.placement

    faces = _cuboid_faces(
        x=p.x,
        y=p.y,
        z=p.z,
        dx=p.w,
        dy=p.d,
        dz=p.h,
    )

    poly = Poly3DCollection(
        faces,
        facecolors=color,
        edgecolors="black",
        linewidths=0.7,
        alpha=0.75,
    )
    ax.add_collection3d(poly)

    if annotate:
        cx = p.x + p.w / 2
        cy = p.y + p.d / 2
        cz = p.z + p.h / 2
        ax.text(
            cx,
            cy,
            cz,
            str(box.box_id),
            fontsize=7,
            ha="center",
            va="center",
        )


# ----------------------------------------
# 단일 pallet 시각화
# ----------------------------------------

def plot_single_pallet_3d(
    pallet,
    figsize: Tuple[int, int] = (10, 8),
    annotate_boxes: bool = True,
    elev: int = 24,
    azim: int = -58,
    show: bool = True,
    save_path: str | None = None,
):
    """
    pallet 1개를 3D 시각화한다.

    Parameters
    ----------
    pallet :
        pallet 객체
    figsize : tuple
        matplotlib figure 크기
    annotate_boxes : bool
        박스 중앙에 box_id 라벨 표시 여부
    elev, azim : int
        3D 시점 조절
    show : bool
        plt.show() 호출 여부
    save_path : str | None
        지정하면 PNG로 저장
    """
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection="3d")

    _draw_pallet_wireframe(ax, pallet)

    packed_boxes = list(pallet.packed_boxes)
    colors = _generate_distinct_colors(len(packed_boxes))

    for packed, color in zip(packed_boxes, colors):
        _draw_box(ax, packed, color=color, annotate=annotate_boxes)

    # 축 범위 설정
    ax.set_xlim(0, pallet.width)
    ax.set_ylim(0, pallet.depth)
    ax.set_zlim(0, pallet.max_height)

    # 축 라벨
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")

    # 보기 각도
    ax.view_init(elev=elev, azim=azim)

    # 제목 정보
    load_factor = _compute_pallet_load_factor(pallet)
    title = (
        f"{pallet.pallet_id} | region={pallet.region} | "
        f"boxes={pallet.num_boxes} | "
        f"weight={getattr(pallet, 'total_weight', 0.0):.2f} | "
        f"height={getattr(pallet, 'used_height', 0)} | "
        f"load_factor={load_factor:.3f}"
    )
    ax.set_title(title)

    # 비율 대충 맞춤
    try:
        ax.set_box_aspect((pallet.width, pallet.depth, pallet.max_height))
    except Exception:
        pass

    plt.tight_layout()

    if save_path is not None:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=200, bbox_inches="tight")

    if show:
        plt.show()
    else:
        plt.close(fig)


# ----------------------------------------
# env 전체 pallet 요약 / 저장
# ----------------------------------------

def _collect_target_pallets(
    env,
    include_open: bool = True,
    include_finished: bool = True,
):
    pallets = []

    if include_open:
        pallets.extend(env.state.open_pallets)

    if include_finished:
        pallets.extend(env.state.finished_pallets)

    return pallets


def print_env_pallet_summaries(
    env,
    include_open: bool = True,
    include_finished: bool = True,
):
    """
    env 내 pallet 요약 정보를 터미널에 출력.
    """
    pallets = _collect_target_pallets(
        env,
        include_open=include_open,
        include_finished=include_finished,
    )

    print("\n========== PALLET SUMMARY ==========")
    if not pallets:
        print("No pallets to summarize.")
        return

    for pallet in pallets:
        lf = _compute_pallet_load_factor(pallet)
        print(
            f"{pallet.pallet_id} | "
            f"region={pallet.region} | "
            f"boxes={pallet.num_boxes} | "
            f"weight={getattr(pallet, 'total_weight', 0.0):.2f} | "
            f"height={getattr(pallet, 'used_height', 0)} | "
            f"load_factor={lf:.3f}"
        )


def save_env_pallet_visualizations(
    env,
    output_dir: str = "visualization/outputs",
    include_open: bool = True,
    include_finished: bool = True,
    annotate_boxes: bool = True,
    elev: int = 24,
    azim: int = -58,
):
    """
    env 내 pallet들을 각각 PNG 파일로 저장한다.

    파일명 예시
    ----------
    pallet_A_1.png
    pallet_B_2.png
    """
    pallets = _collect_target_pallets(
        env,
        include_open=include_open,
        include_finished=include_finished,
    )

    os.makedirs(output_dir, exist_ok=True)

    if not pallets:
        print("[VIS] No pallets found.")
        return

    for pallet in pallets:
        save_path = os.path.join(output_dir, f"{pallet.pallet_id}.png")
        plot_single_pallet_3d(
            pallet=pallet,
            annotate_boxes=annotate_boxes,
            elev=elev,
            azim=azim,
            show=False,
            save_path=save_path,
        )
        print(f"[VIS SAVED] {save_path}")
        
def save_final_pallet_visualizations(
    env,
    step_count: int,
    base_dir: str = "experiments",
):
    """
    실험이 끝난 뒤,
    experiments/YYYYMMDD_stepXXX/
        region_A_1.png
        region_B_2.png
    형태로 저장한다.
    """

    # 날짜 + step 폴더 생성
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_dir_name = f"{now_str}_step{step_count}"

    output_dir = os.path.join(base_dir, exp_dir_name)
    os.makedirs(output_dir, exist_ok=True)

    pallets = env.state.open_pallets + env.state.finished_pallets

    if not pallets:
        print("[VIS] No pallets found.")
        return

    for pallet in pallets:
        filename = pallet.pallet_id.replace("pallet_", "region_") + ".png"
        save_path = os.path.join(output_dir, filename)

        plot_single_pallet_3d(
            pallet=pallet,
            annotate_boxes=True,
            show=False,
            save_path=save_path,
        )

        print(f"[VIS SAVED] {save_path}")

    print(f"\n[VIS DONE] saved to: {output_dir}")