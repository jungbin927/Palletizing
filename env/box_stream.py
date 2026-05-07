"""
box_stream.py

실험에서 사용할 박스 도착 스트림(box stream)을 생성한다.

현재 버전에서는 실제 물류 데이터 대신 synthetic generator를 사용한다.
다만 완전 랜덤 박스 크기 대신, 110 x 110 팔레트에 적합한 7개 표준 박스 타입을 사용한다.

구성:
- product_name: 물류/이커머스에서 자주 다루는 50개 상품명 pool에서 랜덤 샘플링
- 박스 크기: 7개 표준 타입
- 무게: 상품명 특성에 따라 대략적인 범위에서 랜덤 샘플링
"""

import random
from typing import List

from core.types import Box
from configs.default_config import EnvConfig


# -----------------------------
# 1. 110 x 110 pallet 기준 박스 타입 정의
# -----------------------------

BOX_TYPES = {
    "S_flat": {
        "width": 20,
        "depth": 30,
        "height": 10,
    },
    "S_cube": {
        "width": 25,
        "depth": 25,
        "height": 20,
    },
    "M_box": {
        "width": 30,
        "depth": 40,
        "height": 25,
    },
    "M_tall": {
        "width": 30,
        "depth": 30,
        "height": 40,
    },
    "L_flat": {
        "width": 50,
        "depth": 40,
        "height": 15,
    },
    "L_box": {
        "width": 50,
        "depth": 50,
        "height": 30,
    },
    "Long_box": {
        "width": 45,
        "depth": 25,
        "height": 20,
    },
}


# -----------------------------
# 2. 상품명 50개 pool
# -----------------------------

PRODUCT_PROFILES = {
    # 음료/액체류
    "bottled water": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (12, 20),
        "fragile": False,
    },
    "sparkling water cans": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (10, 18),
        "fragile": False,
    },
    "fruit juice bottles": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (10, 18),
        "fragile": False,
    },
    "sports drink bottles": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (10, 18),
        "fragile": False,
    },
    "coffee cans": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (6, 14),
        "fragile": False,
    },
    "milk cartons": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (8, 16),
        "fragile": False,
    },
    "glass soda bottles": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (10, 18),
        "fragile": True,
    },
    "tea bottles": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (8, 16),
        "fragile": False,
    },

    # 세제/청소/생활 액체류
    "liquid laundry detergent": {
        "box_types": ["M_tall", "L_box"],
        "weight_range": (8, 18),
        "fragile": False,
    },
    "powder laundry detergent": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (8, 18),
        "fragile": False,
    },
    "fabric softener": {
        "box_types": ["M_tall", "L_box"],
        "weight_range": (8, 16),
        "fragile": False,
    },
    "dishwashing liquid": {
        "box_types": ["M_tall", "M_box"],
        "weight_range": (6, 14),
        "fragile": False,
    },
    "bleach bottles": {
        "box_types": ["M_tall", "L_box"],
        "weight_range": (8, 18),
        "fragile": False,
    },
    "bathroom cleaner spray": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (4, 10),
        "fragile": False,
    },
    "shampoo bottles": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (4, 12),
        "fragile": False,
    },
    "hand soap refill packs": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (4, 12),
        "fragile": False,
    },

    # 전자제품
    "laptop computer": {
        "box_types": ["M_box", "L_flat"],
        "weight_range": (4, 10),
        "fragile": True,
    },
    "desktop monitor": {
        "box_types": ["L_flat", "L_box"],
        "weight_range": (6, 14),
        "fragile": True,
    },
    "tablet device": {
        "box_types": ["S_flat", "S_cube"],
        "weight_range": (2, 6),
        "fragile": True,
    },
    "wireless speaker": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (3, 8),
        "fragile": True,
    },
    "printer box": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (8, 18),
        "fragile": True,
    },
    "camera lens package": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (2, 8),
        "fragile": True,
    },
    "computer accessories": {
        "box_types": ["S_flat", "S_cube"],
        "weight_range": (2, 7),
        "fragile": True,
    },
    "small home appliance": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (5, 15),
        "fragile": True,
    },

    # 유리/도자기류
    "wine glass set": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (3, 8),
        "fragile": True,
    },
    "ceramic mug set": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (4, 10),
        "fragile": True,
    },
    "glass jar package": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (4, 12),
        "fragile": True,
    },
    "tableware set": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (6, 14),
        "fragile": True,
    },
    "fragile vase box": {
        "box_types": ["M_tall", "M_box"],
        "weight_range": (3, 8),
        "fragile": True,
    },
    "glass food container set": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (4, 10),
        "fragile": True,
    },
    "ceramic plate set": {
        "box_types": ["M_box", "L_flat"],
        "weight_range": (5, 12),
        "fragile": True,
    },
    "fragile ornament box": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (2, 7),
        "fragile": True,
    },

    # 의류/섬유류
    "cotton t-shirts": {
        "box_types": ["S_flat", "S_cube"],
        "weight_range": (2, 6),
        "fragile": False,
    },
    "winter jacket": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (3, 8),
        "fragile": False,
    },
    "denim pants": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (3, 8),
        "fragile": False,
    },
    "sportswear package": {
        "box_types": ["S_flat", "S_cube"],
        "weight_range": (2, 6),
        "fragile": False,
    },
    "socks bundle": {
        "box_types": ["S_flat", "S_cube"],
        "weight_range": (1, 5),
        "fragile": False,
    },
    "knitwear package": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (2, 7),
        "fragile": False,
    },
    "shoe box": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (2, 8),
        "fragile": False,
    },
    "bedding textile pack": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (4, 10),
        "fragile": False,
    },

    # 기타 일반 물품
    "books package": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (5, 15),
        "fragile": False,
    },
    "office supplies box": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (3, 10),
        "fragile": False,
    },
    "toy package": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (2, 8),
        "fragile": False,
    },
    "plastic storage box": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (3, 10),
        "fragile": False,
    },
    "kitchen utensils": {
        "box_types": ["S_cube", "M_box"],
        "weight_range": (3, 12),
        "fragile": False,
    },
    "paper towels pack": {
        "box_types": ["L_flat", "L_box"],
        "weight_range": (2, 7),
        "fragile": False,
    },
    "toilet paper bundle": {
        "box_types": ["L_flat", "L_box"],
        "weight_range": (2, 7),
        "fragile": False,
    },
    "pet supplies": {
        "box_types": ["M_box", "L_box"],
        "weight_range": (5, 16),
        "fragile": False,
    },
    "camping equipment": {
        "box_types": ["M_box", "Long_box", "L_box"],
        "weight_range": (5, 18),
        "fragile": False,
    },
    "gardening tools": {
        "box_types": ["Long_box", "L_box"],
        "weight_range": (5, 20),
        "fragile": False,
    },
}


PRODUCT_NAMES = list(PRODUCT_PROFILES.keys())


def generate_box_stream(config: EnvConfig) -> List[Box]:
    """
    실험용 박스 도착 스트림을 생성한다.
    """

    rng = random.Random(config.seed)
    boxes: List[Box] = []

    for t in range(config.episode_num_boxes):
        region = rng.choice(config.region_names)

        product_name = rng.choice(PRODUCT_NAMES)
        product_profile = PRODUCT_PROFILES[product_name]

        box_type_name = rng.choice(product_profile["box_types"])
        box_type = BOX_TYPES[box_type_name]

        width = box_type["width"]
        depth = box_type["depth"]
        height = box_type["height"]

        weight_min, weight_max = product_profile["weight_range"]
        weight = rng.randint(weight_min, weight_max)

        fragile = product_profile["fragile"]

        box = Box(
            box_id=f"box_{t}",
            width=width,
            depth=depth,
            height=height,
            weight=weight,
            region=region,
            arrival_time=t,
            fragile=fragile,
            category=None,
            product_name=product_name,
        )

        boxes.append(box)

    boxes.sort(key=lambda b: b.arrival_time)
    return boxes