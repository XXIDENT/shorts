"""직업별 무대. props: (소품 이름, x, {옵션}), spots: 모니가 설 자리(x), npc: 손님 자리(x)."""
from __future__ import annotations

from .art import C, FLOOR

B = FLOOR + 18          # 뒷줄 소품 바닥선
TOP = B - 22            # 카운터 윗면

SCENES = {
    "cafe": {
        "wall": (236, 214, 180), "wall2": (220, 196, 160), "floor": (150, 100, 70), "time": "morning",
        "decor": [("clock", 126, {"y": 16}), ("poster", 96, {"y": 34, "c": C["teal"]})],
        "props": [("plant", 4, {"y": B}), ("counter", 60, {"y": B, "w": 116}),
                  ("register", 70, {"y": TOP}), ("cup", 104, {"y": TOP}), ("cup", 112, {"y": TOP, "c": C["pink"]}),
                  ("coffee", 150, {"y": TOP})],
        "spots": {"enter": -20, "center": 90, "machine": 140, "register": 84, "cups": 112, "left": 40},
        "npc": 30,
    },
    "bar": {
        "wall": (60, 44, 70), "wall2": (74, 54, 86), "floor": (70, 50, 50), "time": "night", "window": False,
        "decor": [("bottles", 100, {"y": 70, "w": 70}), ("poster", 20, {"y": 30, "c": C["purple"]})],
        "props": [("counter", 50, {"y": B, "w": 126, "c": C["dbrown"]}), ("cup", 90, {"y": TOP, "c": C["glass"]}),
                  ("cup", 130, {"y": TOP, "c": C["orange"]})],
        "spots": {"enter": -20, "center": 100, "shelf": 140, "counter": 110, "left": 40},
        "npc": 26,
    },
    "bakery": {
        "wall": (250, 228, 200), "wall2": (240, 210, 180), "floor": (200, 160, 120), "time": "morning",
        "decor": [("clock", 70, {"y": 14})],
        "props": [("bread", 100, {"y": B}), ("bread", 128, {"y": B}), ("oven", 146, {"y": B}),
                  ("counter", 2, {"y": B, "w": 60})],
        "spots": {"enter": -20, "center": 90, "oven": 150, "rack": 116, "counter": 40},
        "npc": 22,
    },
    "kitchen": {
        "wall": (220, 230, 236), "wall2": (200, 214, 222), "floor": (120, 130, 140), "time": "day",
        "window_x": 70, "decor": [("clock", 130, {"y": 14})],
        "props": [("fridge", 4, {"y": B}), ("sink", 34, {"y": B}), ("dishes", 40, {"y": B - 22}),
                  ("stove", 120, {"y": B}), ("counter", 66, {"y": B, "w": 52, "c": C["steel"]})],
        "spots": {"enter": -20, "center": 90, "stove": 136, "sink": 50, "fridge": 18, "board": 90},
        "npc": 160,
    },
    "office": {
        "wall": (200, 210, 224), "wall2": (184, 196, 212), "floor": (90, 100, 120), "time": "day",
        "decor": [("clock", 70, {"y": 14}), ("poster", 140, {"y": 30, "c": C["blue"]})],
        "props": [("plant", 4, {"y": B}), ("desk_pc", 40, {"y": B}), ("phone", 84, {"y": B - 16}),
                  ("desk_pc", 110, {"y": B, "screen": C["teal"]})],
        "spots": {"enter": -20, "center": 90, "desk": 62, "desk2": 130, "phone": 88},
        "npc": 160,
    },
    "store": {
        "wall": (236, 240, 230), "wall2": (220, 226, 214), "floor": (200, 204, 196), "time": "night",
        "window_x": 128,
        "props": [("shelf", 4, {"y": B, "seed": 3}), ("shelf", 46, {"y": B, "seed": 8}),
                  ("counter", 100, {"y": B, "w": 76, "c": C["lgrey"]}), ("register", 140, {"y": TOP})],
        "spots": {"enter": -20, "center": 90, "register": 146, "shelf": 40, "door": 10},
        "npc": 90,
    },
    "salon": {
        "wall": (250, 220, 230), "wall2": (240, 200, 214), "floor": (230, 230, 236), "time": "day",
        "window": False,
        "props": [("chair_mirror", 30, {"y": B}), ("chair_mirror", 100, {"y": B}), ("plant", 160, {"y": B})],
        "spots": {"enter": -20, "center": 90, "chair": 70, "chair2": 140, "left": 20},
        "npc": 45,
    },
    "clinic": {
        "wall": (220, 240, 236), "wall2": (200, 228, 222), "floor": (180, 200, 200), "time": "day",
        "decor": [("clock", 130, {"y": 16})],
        "props": [("bed", 60, {"y": B}), ("iv", 108, {"y": B}), ("monitor", 40, {"y": B})],
        "spots": {"enter": -20, "center": 90, "bed": 84, "iv": 124, "desk": 30},
        "npc": 150,
    },
    "vet": {
        "wall": (226, 236, 210), "wall2": (210, 224, 190), "floor": (170, 180, 150), "time": "day",
        "decor": [("poster", 140, {"y": 30, "c": C["green"]})],
        "props": [("table", 60, {"y": B, "w": 46}), ("dog", 70, {"y": B - 18}), ("cat", 140, {"y": B})],
        "spots": {"enter": -20, "center": 90, "table": 112, "cat": 130, "left": 30},
        "npc": 30,
    },
    "street": {
        "wall": (110, 180, 245), "floor": (90, 94, 104), "floor2": (150, 150, 160), "outdoor": True,
        "road": True, "time": "day",
        "decor": [("building", 0, {"y": FLOOR, "w": 44, "h": 96, "c": (170, 160, 150)}),
                  ("building", 48, {"y": FLOOR, "w": 36, "h": 70, "c": (150, 160, 180)}),
                  ("building", 130, {"y": FLOOR, "w": 50, "h": 104, "c": (180, 170, 190)}),
                  ("streetlamp", 100, {"y": FLOOR})],
        "props": [],
        "spots": {"enter": -20, "center": 90, "left": 40, "right": 140},
        "npc": 150,
    },
    "studio": {
        "wall": (60, 60, 72), "wall2": (52, 52, 62), "floor": (80, 80, 92), "time": "day", "window": False,
        "props": [("backdrop", 50, {"y": B}), ("softbox", 10, {"y": B}), ("softbox", 150, {"y": B}),
                  ("tripod", 130, {"y": B + 8})],
        "spots": {"enter": -20, "center": 90, "camera": 132, "stage": 90, "left": 40},
        "npc": 90,
    },
    "classroom": {
        "wall": (236, 230, 200), "wall2": (222, 214, 180), "floor": (170, 130, 90), "time": "morning",
        "window_x": 128, "decor": [("clock", 100, {"y": 10})],
        "props": [("board", 20, {"y": B}), ("desk", 100, {"y": B + 10}), ("desk", 140, {"y": B + 10})],
        "spots": {"enter": -20, "center": 90, "board": 52, "desks": 120},
        "npc": 150,
    },
    "library": {
        "wall": (210, 190, 160), "wall2": (196, 174, 142), "floor": (120, 80, 60), "time": "evening",
        "window_x": 70,
        "props": [("books", 2, {"y": B}), ("books", 130, {"y": B, "seed": 9, "w": 48}),
                  ("desk", 60, {"y": B, "w": 60})],
        "spots": {"enter": -20, "center": 90, "shelf": 30, "shelf2": 150, "desk": 90},
        "npc": 150,
    },
    "field": {
        "wall": (110, 180, 245), "floor": (80, 160, 80), "floor2": (100, 180, 90), "outdoor": True,
        "time": "day",
        "decor": [("tree", 10, {"y": FLOOR}), ("tree", 160, {"y": FLOOR})],
        "props": [("field_lines", 0, {"y": B}), ("goal", 130, {"y": B})],
        "spots": {"enter": -20, "center": 90, "goal": 120, "left": 40},
        "npc": 50,
    },
    "home": {
        "wall": (230, 214, 236), "wall2": (214, 196, 222), "floor": (160, 120, 100), "time": "evening",
        "decor": [("poster", 130, {"y": 30, "c": C["yellow"]})],
        "props": [("sofa", 70, {"y": B}), ("plant", 150, {"y": B}), ("boxes", 6, {"y": B})],
        "spots": {"enter": -20, "center": 90, "sofa": 90, "boxes": 30},
        "npc": 150,
    },
}
