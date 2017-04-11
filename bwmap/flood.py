from math import sqrt, inf
from typing import Tuple, Set, Callable
from itertools import product

import numpy as np


SQ2 = sqrt(2)


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


def flood(
    shape: Tuple[int, int],
    start_points: Set[Tuple[int, int]],
    wall_predicate: Callable[[int, int], bool],
    max_distance: float=inf
):
    """
    Fills matrix with distances from start_points.
    Walls constraint the flow of flood, leaving wall cells as infinitely far.
    max_distance stops the flow from too wide unnecessary spreading (lesser value = faster calculation)
    """

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


def filled_mask_from_func(shape: Tuple[int, int], predicate: Callable[[int, int], bool]) -> np.ndarray:
    """
    Makes boolean 2d np.array from predicate
    wall is True
    """
    result = np.empty(shape, dtype=np.bool_)
    for y in range(shape[0]):
        for x in range(shape[1]):
            result[y, x] = predicate(x, y)
    return result


def find_locations_for_sized_object(wallmask: np.ndarray, sizex: int, sizey: int) -> np.ndarray:
    """
    Searches positions for sized rectangular object on boolean 2d np.array
    produced by filled_mask_from_func.
    There must bee no wall in rectangular area.
    Top-left corner coordinates returned
    """
    shape = wallmask.shape
    output = np.zeros(shape, dtype=np.bool_)
    for y in range(shape[0] - sizey):
        for x in range(shape[1] - sizex):
            output[y, x] = not wallmask[y:y + sizey, x:x + sizex].any()
    return np.where(output)


def find_maximums(data: np.ndarray) -> np.ndarray:
    """
    Searching all local maximums for 2d array.
    Result is a matrix of bools
    True means this is a local maximum or a plato.
    """
    mask = np.ones(data.shape, dtype=np.bool_)
    fwd, back, full = (1, None), (None, -1), (None, None)
    inversion = {fwd: back, back: fwd, full: full}
    for ys, xs in product((fwd, back, full), repeat=2):
        if ys == full and xs == full:
            continue
        ms = (slice(*ys), slice(*xs))
        mask[ms] &= data[ms] >= data[slice(*inversion[ys]), slice(*inversion[xs])]
    return mask


def summarize_for_greater_scale(data: np.ndarray, divide: int) -> np.ndarray:
    """
    Calculates sums for rectanglar tiles of size [divide x divide]
    Result is a smaller matrix.
    """
    shape = data.shape
    out_shape = tuple(v // divide for v in shape)
    output = np.empty(out_shape)
    for y in range(0, shape[0], divide):
        for x in range(0, shape[1], divide):
            output[y // divide, x // divide] = data[y:y + divide, x:x + divide].sum()
    return output
