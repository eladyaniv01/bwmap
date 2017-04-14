from functools import lru_cache
from collections import defaultdict

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
            yield x * sz, y * sz, sz, sz
        else:
            if level + 1 >= len(self.levels):
                return
            for dx in (0, 1):
                for dy in (0, 1):
                    yield from self.iter_nodes(level + 1, x * 2 + dx, y * 2 + dy)


class NodeMerger:
    def __init__(self, nodelist):
        self.nodes = {i: node for i, node in enumerate(nodelist)}
        self._build_side_index()

    @staticmethod
    def _node_sides(node):
        x, y, szx, szy = node
        # True vertical, False horizontal
        # +- 0 -+
        # 3     1
        # +- 2 -+
        yield 0, (False, x, y, szx)
        yield 1, (True, x + szx, y, szy)
        yield 2, (False, x, y + szy, szx)
        yield 3, (True, x, y, szy)

    def _push_node_sides(self, nid, node):
        for side, key in self._node_sides(node):
            self.side_index[key].add((nid, side))

    def _pop_node_sides(self, nid, node):
        for side, key in self._node_sides(node):
            self.side_index[key].remove((nid, side))

    def _build_side_index(self):
        self.side_index = defaultdict(lambda: set())
        for i, node in self.nodes.items():
            self._push_node_sides(i, node)

    def _grow_down(self, key, id1, side1, id2, side2):
        assert side1 == 2
        assert side2 == 0

        node2 = self.nodes.pop(id2)
        self._pop_node_sides(id2, node2)
        self._pop_node_sides(id1, self.nodes[id1])
        x, y, szx, szy = self.nodes[id1]
        self.nodes[id1] = x, y, szx, szy + node2[3]
        self._push_node_sides(id1, self.nodes[id1])

    def _grow_right(self, key, id1, side1, id2, side2):
        assert side1 == 1
        assert side2 == 3

        node2 = self.nodes.pop(id2)
        self._pop_node_sides(id2, node2)
        self._pop_node_sides(id1, self.nodes[id1])
        x, y, szx, szy = self.nodes[id1]
        self.nodes[id1] = x, y, szx + node2[2], szy
        self._push_node_sides(id1, self.nodes[id1])

    def _merge_side(self, key):
        if len(self.side_index[key]) != 2:
            return False
        (id1, side1), (id2, side2) = self.side_index[key]
        if side1 == 0:
            self._grow_down(key, id2, side2, id1, side1)
        elif side1 == 1:
            self._grow_right(key, id1, side1, id2, side2)
        elif side1 == 2:
            self._grow_down(key, id1, side1, id2, side2)
        else:
            self._grow_right(key, id2, side2, id1, side1)
        return True

    def _merge_step(self, min_side_size):
        keys = []
        for key, ids in self.side_index.items():
            assert len(ids) in (0, 1, 2)
            if len(ids) == 2 and key[3] >= min_side_size:
                keys.append(key)

        count = 0
        for key in keys:
            if self._merge_side(key):
                count += 1
        return count

    def _max_node_size(self):
        result = 0
        for x, y, sx, sy in self.nodes.values():
            result = max(result, sx, sy)
        return result

    def merge(self):
        sz = self._max_node_size()
        while sz >= 1:
            while True:
                count = self._merge_step(sz)
                print(sz, count)
                if count == 0:
                    break
            sz //= 2

    def iter_nodes(self):
        return self.nodes.values()
