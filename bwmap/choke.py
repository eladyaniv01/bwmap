from functools import lru_cache

import numpy as np

from .metrics import MapMetrics


def step_off(data: np.ndarray):
    return data[::2, ::2] & data[1::2, ::2] & data[::2, 1::2] & data[1::2, 1::2]


def build_quadtree_levels(data: np.ndarray):
    levels = [data]
    while min(*data.shape) > 1:
        data = step_off(data)
        levels.append(data)
    return list(reversed(levels))


class ChokeFinder:
    def __init__(self, game, mm: MapMetrics):
        self.game = game
        self.mm = mm

    def __call__(self):
        self.levels = build_quadtree_levels(self.mm.get_walkability_map())

    @lru_cache(100)
    def node_size(self, level):
        return 2 ** (len(self.levels) - level - 1)

    def iter_nodes(self, level=0, x=0, y=0):
        if self.levels[level][y, x]:
            sz = self.node_size(level)
            yield x * sz, y * sz, sz
        else:
            if level + 1 >= len(self.levels):
                return
            for dx in (0, 1):
                for dy in (0, 1):
                    yield from self.iter_nodes(level + 1, x * 2 + dx, y * 2 + dy)
