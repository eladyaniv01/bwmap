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


class BaseNodeMerger:
    WALL_ID = 0
    EMPTY_ID = 1

    def __init__(self, nodelist):
        self.nodes = {i: node for i, node in enumerate(nodelist, start=2)}
        self._prepare()

    def _prepare(self):
        pass

    def __call__(self):
        raise NotImplementedError

    def __iter__(self):
        return iter(self.nodes.values())


class SameSideNodeMerger(BaseNodeMerger):
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

    def _prepare(self):
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

    def __call__(self):
        sz = self._max_node_size()
        while sz >= 1:
            while True:
                count = self._merge_step(sz)
                print(sz, count)
                if count == 0:
                    break
            sz //= 2


class GrowthNodeMerger(BaseNodeMerger):
    def _place_node(self, nid, check=True):
        x, y, sx, sy = self.nodes[nid]
        if check:
            assert (self.map[y:y + sy, x:x + sx] == self.EMPTY_ID).all()
        self.map[y:y + sy, x:x + sx] = nid
        self.areas[nid] = sx * sy

    def _prepare(self):
        mx, my = 0, 0
        for x, y, sx, sy in self.nodes.values():
            mx = max(mx, x + sx)
            my = max(my, y + sy)
        self.mx, self.my = mx, my

        self.map = np.full((mx, my), self.WALL_ID, dtype=np.int_)
        self.areas = {}
        for nid in self.nodes.keys():
            self._place_node(nid, check=False)

        self.new_id = len(self.nodes) + 5

    def _allocate_id(self):
        self.new_id += 1
        return self.new_id

    def _clear_node_map(self, nid):
        x, y, sx, sy = self.nodes[nid]
        self.map[y:y + sy, x:x + sx] = self.EMPTY_ID

    def _remove_node(self, nid):
        self._clear_node_map(nid)
        del self.nodes[nid]
        del self.areas[nid]

    def _split4_node(self, nid, splitx: int, splity: int):
        """
        Returned ids:
        [top-left, top-right, bottom-right, bottom-left]
        """
        x, y, sx, sy = self.nodes[nid]
        assert x <= splitx <= x + sx, '{} < {} < {}'.format(x, splitx, x + sx)
        assert y <= splity <= y + sy

        self._remove_node(nid)
        ids = [self._allocate_id() for _ in range(4)]

        s1x, s1y = splitx - x, splity - y
        s2x = sx - (splitx - x)
        s2y = sy - (splity - y)

        self.nodes[ids[0]] = x, y, s1x, s1y
        self.nodes[ids[1]] = splitx, y, s2x, s1y
        self.nodes[ids[2]] = splitx, splity, s2x, s2y
        self.nodes[ids[3]] = x, splity, s1x, s2y

        for i in ids:
            self._place_node(i)
        return ids

    def _cleanup_empty_nodes(self, ids):
        for i in ids:
            if i not in self.nodes:
                continue
            if self.areas[i] == 0:
                self._remove_node(i)

    def _cut_node(self, nid, side, amount):
        self._clear_node_map(nid)
        x, y, sx, sy = self.nodes[nid]

        if amount >= sy if side in (0, 2) else amount >= sx:
            self._remove_node(nid)
            return

        if side == 0:
            y += amount
        elif side == 3:
            x += amount

        if side in (0, 2):
            sy -= amount
        else:
            sx -= amount

        self.nodes[nid] = x, y, sx, sy
        self._place_node(nid)

    @staticmethod
    def _is_range_in(a1, b1, a2, b2):
        "1 inside 2"
        assert a1 < b1
        assert a2 < b2
        return (
            a2 <= a1 <= b2 and
            a2 <= b1 <= b2
        )

    @classmethod
    def _get_split_side(cls, side, a1, b1, a2, b2):
        "1 - to be splitted, 2 - intruding shape"
        assert a1 < b1
        assert a2 < b2
        straight = side < 2
        if cls._is_range_in(a1, b1, a2, b2):
            return 'inside'
        if b1 <= b2:
            return 'left' if straight else 'right'
        if a1 >= a2:
            return 'right' if straight else 'left'
        return 'both'

    _PRECHECK = [
        lambda x, y, sx, sy, mx, my: y > 0,
        lambda x, y, sx, sy, mx, my: x + sx < mx - 1,
        lambda x, y, sx, sy, mx, my: y + sy < my - 1,
        lambda x, y, sx, sy, mx, my: x > 0,
    ]
    _SLICES = [
        lambda x, y, sx, sy: (slice(y - 1, y), slice(x, x + sx)),
        lambda x, y, sx, sy: (slice(y, y + sy), slice(x + sx, x + sx + 1)),
        lambda x, y, sx, sy: (slice(y + sy, y + sy + 1), slice(x, x + sx)),
        lambda x, y, sx, sy: (slice(y, y + sy), slice(x - 1, x)),
    ]
    _LEFT = [
        lambda x, y, sx, sy: (x, y - 1),
        lambda x, y, sx, sy: (x + sx + 1, y),
        lambda x, y, sx, sy: (x + sx, y + sy + 1),
        lambda x, y, sx, sy: (x - 1, y + sy),
    ]
    _RIGHT = [
        lambda x, y, sx, sy: (x + sx, y - 1),
        lambda x, y, sx, sy: (x + sx + 1, y + sy),
        lambda x, y, sx, sy: (x, y + sy + 1),
        lambda x, y, sx, sy: (x - 1, y),
    ]
    _AFTER = [
        lambda x, y, sx, sy: (x, y - 1, sx, sy + 1),
        lambda x, y, sx, sy: (x, y, sx + 1, sy),
        lambda x, y, sx, sy: (x, y, sx, sy + 1),
        lambda x, y, sx, sy: (x - 1, y, sx + 1, sy),
    ]

    def _grow_side(self, nid, side):
        node = self.nodes[nid]
        if not self._PRECHECK[side](*node, self.mx, self.my):
            return False
        map_chunk = self.map[self._SLICES[side](*node)]
        if (map_chunk == self.WALL_ID).any():
            return False

        self._clear_node_map(nid)
        affected_ids = np.unique(map_chunk)
        vert = side % 2
        for i in affected_ids:
            target = self.nodes[i]
            smode = self._get_split_side(
                side,
                target[vert], target[vert] + target[2 + vert],
                node[vert], node[vert] + node[2 + vert],
            )
            if smode == 'inside':
                self._cut_node(i, (side + 2) % 4, 1)
            elif smode == 'left':
                ids = self._split4_node(i, *self._LEFT[side](*node))
                self._remove_node(ids[(side + 2) % 4])
                self._cleanup_empty_nodes(ids)
            elif smode == 'right':
                ids = self._split4_node(i, *self._RIGHT[side](*node))
                self._remove_node(ids[(side + 3) % 4])
                self._cleanup_empty_nodes(ids)
            elif smode == 'both':
                ids = self._split4_node(i, *self._LEFT[side](*node))
                self._cut_node(ids[(side + 2) % 4], (side + 3) % 4, node[2 + vert])
                self._cleanup_empty_nodes(ids)

        self.nodes[nid] = self._AFTER[side](*node)
        self._place_node(nid)
        return True

    def _grow_node(self, nid):
        for side in range(4):
            while self._grow_side(nid, side):
                pass

    def __call__(self):
        for i, area in sorted(self.areas.items(), key=lambda x: x[1], reverse=True):
            if i not in self.nodes:
                continue
            print(i, area)
            self._grow_node(i)
