import numpy as np


def make_metric_filled_matrix(shape, start):
    # Currently unused
    dims = np.indices(shape)
    for dim, coord in zip(dims, start):
        np.square(dim - coord, out=dim)
    return np.sqrt(np.sum(dims, axis=0))


def _get_bool_map(shape, predicate):
    result = np.empty(shape, dtype=np.bool_)
    for y in range(shape[0]):
        for x in range(shape[1]):
            result[y, x] = predicate(x, y)
    return result


class MapMetrics:
    def __init__(self, game, WALKPOSITION_SCALE, TILEPOSITION_SCALE):
        self.game = game
        self.WS = WALKPOSITION_SCALE
        self.BS = TILEPOSITION_SCALE
        self.BWS = self.BS // self.WS
        assert self.BS % self.WS == 0

    def get_map_shape(self, scale=None):
        if scale is None:
            scale = self.WS
        return (self.game.mapHeight() * self.BS // scale, self.game.mapWidth() * self.BS // scale)

    def get_unit_bounds(self, u, scale=None):
        if scale is None:
            scale = self.WS
        return (
            u.getLeft() // scale, u.getRight() // scale + 1,
            u.getTop() // scale, u.getBottom() // scale + 1,
        )

    def get_unit_center_point(self, u, scale=None):
        if scale is None:
            scale = self.WS
        return (
            (u.getRight() + u.getLeft()) // 2 // scale,
            (u.getBottom() + u.getTop()) // 2 // scale,
        )

    def get_walkability_map(self):
        return _get_bool_map(self.get_map_shape(scale=self.WS), self.game.isWalkable)

    def get_builability_map(self):
        return _get_bool_map(self.get_map_shape(scale=self.BS), self.game.isBuildable)

    @classmethod
    def from_pybrood(cls, pybrood):
        return cls(pybrood.game, pybrood.WALKPOSITION_SCALE, pybrood.TILEPOSITION_SCALE)
