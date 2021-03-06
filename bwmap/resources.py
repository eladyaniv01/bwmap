from itertools import chain
from math import inf
from functools import lru_cache

import numpy as np

from .metrics import MapMetrics
from .flood import (
    flood, summarize_for_greater_scale,
    find_locations_for_sized_object, find_maximums,
    make_predicate
)


MINERAL_IMPORTANCE = 1.0
GAS_IMPORTANCE = 0.6

BASE_SIZE = (4, 3)
MINERAL_SIZE = (2, 1)
GEYSER_SIZE = (4, 2)


def unit_tileset(bx, by, w, h):
    sp = set()
    for y in range(by, by + h):
        for x in range(bx, bx + w):
            sp.add((x, y))
    return sp


class BaseFinder:
    def __init__(self, game, mm: MapMetrics):
        self.game = game
        self.mm = mm
        self.FLOOD_DISTANCE = 10 * mm.BWS

    @staticmethod
    def res_per_second(distance):
        return 8 / (4.3 + 0.67 * distance)

    def make_unit_mask(self, scale=None, gap=0):
        """
        Make boolean mask with mineral and geyser units marked as True.
        Resource units behave as walls for workers.
        """
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

    @lru_cache(1)
    def get_walkable_wall_mask(self):
        return self.make_unit_mask() | ~self.mm.get_walkability_map()

    @lru_cache(1)
    def get_buildable_wall_mask(self):
        return self.make_unit_mask(scale=self.mm.BS, gap=3) | ~self.mm.get_builability_map()

    @lru_cache(1)
    def get_possible_base_locations(self):
        yc, xc = find_locations_for_sized_object(
            self.get_buildable_wall_mask(), *BASE_SIZE)
        return yc, xc

    @lru_cache(1)
    def get_possible_base_locations_mask(self):
        "Mostly for debug drawing"
        result = np.zeros(self.mm.get_map_shape(scale=self.mm.BS), dtype=np.bool_)
        yc, xc = self.get_possible_base_locations()
        for dy in range(BASE_SIZE[1]):
            ycc = yc + dy
            for dx in range(BASE_SIZE[0]):
                result[ycc, xc + dx] = True
        return result

    def flood_resource_unit(self, u, max_distance=inf):
        "Fill distances from resource unit"
        bs = self.mm.get_unit_bounds(u)
        return flood(
            self.mm.get_map_shape(),
            unit_tileset(bs[0], bs[2], bs[1] - bs[0], bs[3] - bs[2]),
            make_predicate(self.get_walkable_wall_mask()),
            max_distance=max_distance,
        )

    def flood_base_location(self, btx, bty, wall_predicate, max_distance=inf):
        "Fill distances from base location"
        return flood(
            self.mm.get_map_shape(),
            unit_tileset(*(x * self.mm.BWS for x in (btx, bty, *BASE_SIZE))),
            wall_predicate,
            max_distance=max_distance,
        )

    def resource_unit_scores(self, u):
        """
        Transforms distances from resource into resource availability rating.
        Greater value is better
        """
        distances = self.flood_resource_unit(u, max_distance=self.FLOOD_DISTANCE)
        distances[distances <= 0] = inf
        return np.maximum(
            self.res_per_second(distances / self.mm.BWS) -
            self.res_per_second(self.FLOOD_DISTANCE / self.mm.BWS),
            0
        )

    def all_resource_units_scores(self, iterunits_func):
        "Computes normalized [0..1] sum of ratings (resource_unit_scores) for all resource units"
        resource_scores = np.zeros(self.mm.get_map_shape())
        sz = len(iterunits_func())
        for i, u in enumerate(iterunits_func()):
            resource_scores += self.resource_unit_scores(u)
            print(u.getID(), '{}/{}'.format(i + 1, sz))
        return resource_scores / resource_scores.max()

    def mineral_scoremap(self):
        return self.all_resource_units_scores(self.game.getMinerals)

    def gas_scoremap(self):
        return self.all_resource_units_scores(self.game.getGeysers)

    def resource_scoremap(self):
        return (
            MINERAL_IMPORTANCE * self.mineral_scoremap()
            +
            GAS_IMPORTANCE * self.gas_scoremap()
        )

    def build_place_scores(self, scores):
        yc, xc = self.get_possible_base_locations()
        result = np.zeros_like(scores)
        for y, x in zip(yc, xc):
            result[y, x] = (  # perimeter sum
                scores[y:y + BASE_SIZE[1], x:x + BASE_SIZE[0]].sum() -
                scores[y + 1:y + BASE_SIZE[1] - 1, x + 1:x + BASE_SIZE[0] - 1].sum()
            )
        return result

    def __call__(self):
        resource_scores = self.resource_scoremap()

        btile_scores = summarize_for_greater_scale(resource_scores, self.mm.BWS)
        yc, xc = self.get_possible_base_locations()
        bplace_scores = np.zeros_like(btile_scores)
        for x, y in zip(xc, yc):
            bplace_scores[y, x] = btile_scores[y:y + BASE_SIZE[1], x:x + BASE_SIZE[0]].sum()

        bplace_ext = find_maximums(bplace_scores)
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
            base_distances = self.flood_base_location(
                btx, bty, make_predicate(self.get_walkable_wall_mask()),
                max_distance=self.FLOOD_DISTANCE)

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
