from itertools import chain, product
from typing import Set, Tuple
from math import sqrt, inf

import numpy as np

from .metrics import MapMetrics


SQ2 = sqrt(2)
MINERAL_IMPORTANCE = 1.0
GAS_IMPORTANCE = 0.6

BASE_SIZE = (4, 3)
MINERAL_SIZE = (2, 1)
GEYSER_SIZE = (4, 2)


def next_points(start_points):
    for x, y in start_points:
        yield x, y, x + 1,     y, 1.0
        yield x, y, x - 1,     y, 1.0
        yield x, y,     x, y + 1, 1.0
        yield x, y,     x, y - 1, 1.0
        yield x, y, x + 1, y + 1, SQ2
        yield x, y, x + 1, y - 1, SQ2
        yield x, y, x - 1, y + 1, SQ2
        yield x, y, x - 1, y - 1, SQ2


def flood(shape, start_points: Set[Tuple[int, int]], wall_predicate, max_distance=inf):
    output = np.full(shape, inf)
    for x, y in start_points:
        output[y, x] = 0

    while start_points:
        new_start_points = set()
        for ox, oy, x, y, dist in next_points(start_points):
            if x < 0 or y < 0 or y >= shape[0] or x >= shape[1]:
                continue
            if wall_predicate(x, y):
                continue
            rate = output[oy, ox] + dist
            if rate > max_distance:
                continue
            if rate < output[y, x]:
                output[y, x] = rate
                new_start_points.add((x, y))
        start_points = new_start_points

    return output


def filled_mask_from_func(shape, predicate):
    result = np.empty(shape, dtype=np.bool_)
    for y in range(shape[0]):
        for x in range(shape[1]):
            result[y, x] = predicate(x, y)
    return result


def find_locations_for_sized_object(wallmask, sizex, sizey):
    shape = wallmask.shape
    output = np.zeros(shape, dtype=np.bool_)
    for y in range(shape[0] - sizey):
        for x in range(shape[1] - sizex):
            output[y, x] = not wallmask[y:y + sizey, x:x + sizex].any()
    return np.where(output)


def find_extremums(data):
    mask = np.ones(data.shape, dtype=np.bool_)
    fwd, back, full = (1, None), (None, -1), (None, None)
    inversion = {fwd: back, back: fwd, full: full}
    for ys, xs in product((fwd, back, full), repeat=2):
        if ys == full and xs == full:
            continue
        ms = (slice(*ys), slice(*xs))
        mask[ms] &= data[ms] >= data[slice(*inversion[ys]), slice(*inversion[xs])]
    return mask


def summarize_for_greater_scale(data, divide):
    shape = data.shape
    out_shape = tuple(v // divide for v in shape)
    output = np.empty(out_shape)
    for y in range(0, shape[0], divide):
        for x in range(0, shape[1], divide):
            output[y // divide, x // divide] = data[y:y + divide, x:x + divide].sum()
    return output


class BaseFinder:
    def __init__(self, game, mm: MapMetrics):
        self.game = game
        self.mm = mm
        self.FLOOD_DISTANCE = 15 * mm.BWS

    def flood_resource_unit(self, u, wall_predicate, max_distance=inf):
        sp = set()
        bs = self.mm.get_unit_bounds(u)
        for y in range(bs[2], bs[3]):
            for x in range(bs[0], bs[1]):
                sp.add((x, y))
        return flood(
            self.mm.get_map_shape(),
            sp,
            wall_predicate,
            max_distance=max_distance,
        )

    def flood_base_location(self, btx, bty, wall_predicate, max_distance=inf):
        sp = set()
        for y in range(bty * self.mm.BWS, (bty + BASE_SIZE[1]) * self.mm.BWS):
            for x in range(btx * self.mm.BWS, (btx + BASE_SIZE[0]) * self.mm.BWS):
                sp.add((x, y))
        return flood(
            self.mm.get_map_shape(),
            sp,
            wall_predicate,
            max_distance=max_distance,
        )

    def scoreflood_resource_unit(self, u, wall_predicate):
        max_dist = self.FLOOD_DISTANCE
        distances = self.flood_resource_unit(u, wall_predicate, max_distance=max_dist)
        return np.maximum(u.getResources() * (max_dist - distances), 0)

    def complete_resource_score(self, iterunits_func, wall_predicate):
        resource_scores = np.zeros(self.mm.get_map_shape())
        sz = len(iterunits_func())
        for i, u in enumerate(iterunits_func()):
            resource_scores += self.scoreflood_resource_unit(u, wall_predicate)
            print(u.getID(), '{}/{}'.format(i + 1, sz))
        return resource_scores / resource_scores.max()

    def make_unit_mask(self, scale=None, gap=0):
        "Make boolean mask with mineral and geyser units marked as True"
        if scale is None:
            scale = self.mm.WS
        shape = self.mm.get_map_shape(scale=scale)
        result = np.zeros(shape, dtype=np.bool_)
        for u in chain(self.game.getMinerals(), self.game.getGeysers()):
            bs = self.mm.get_unit_bounds(u, scale=scale)
            result[
                max(bs[2] - gap, 0):min(bs[3] + gap, shape[0]),
                max(bs[0] - gap, 0):min(bs[1] + gap, shape[1])
            ] = True
        return result

    def __call__(self):
        uwm = self.make_unit_mask()

        def wall_predicate(x, y):
            if uwm[y, x]:
                return True
            return not self.game.isWalkable(x, y)

        resource_scores = (
            MINERAL_IMPORTANCE * self.complete_resource_score(self.game.getMinerals, wall_predicate)
            +
            GAS_IMPORTANCE * self.complete_resource_score(self.game.getGeysers, wall_predicate)
        )

        wallm = filled_mask_from_func(
            self.mm.get_map_shape(scale=self.mm.BS),
            lambda x, y: not self.game.isBuildable(x, y)
        ) | self.make_unit_mask(scale=self.mm.BS, gap=3)
        btile_scores = summarize_for_greater_scale(resource_scores, self.mm.BWS)
        btile_scores[wallm] = 0

        yc, xc = find_locations_for_sized_object(wallm, *BASE_SIZE)
        bplace_scores = np.zeros_like(btile_scores)
        for x, y in zip(xc, yc):
            bplace_scores[y, x] = btile_scores[y:y + BASE_SIZE[1], x:x + BASE_SIZE[0]].sum()

        bplace_ext = find_extremums(bplace_scores)
        bplace_ext &= bplace_scores > 0

        all_resource_units = {}
        for u in self.game.getMinerals():
            all_resource_units[u.getID()] = (
                self.mm.get_unit_bounds(u),
                'minerals', u.getResources(),
            )
        for u in self.game.getGeysers():
            all_resource_units[u.getID()] = (
                self.mm.get_unit_bounds(u),
                'gas', u.getResources(),
            )

        possible_bases = [(btx, bty, bplace_scores[bty, btx]) for bty, btx in zip(*np.where(bplace_ext))]
        possible_bases.sort(key=lambda x: -x[2])
        valid_bases = {}
        for i, (btx, bty, base_score) in enumerate(possible_bases):
            base_distances = self.flood_base_location(btx, bty, wall_predicate, max_distance=self.FLOOD_DISTANCE)

            resources_to_pop = set()
            for ruid in all_resource_units.keys():
                rpos = all_resource_units[ruid][0]
                if np.any(base_distances[rpos[2] - 1:rpos[3] + 1, rpos[0] - 1:rpos[1] + 1] < inf):
                    resources_to_pop.add(ruid)

            vb = {
                'score': base_score,
                'resources': [all_resource_units.pop(ruid) for ruid in resources_to_pop],
            }
            if vb['resources']:
                # a base MUST have resources
                valid_bases[(btx, bty)] = vb

            if not all_resource_units:
                # no resources left, leaving loop
                break

        return valid_bases
