from ..metrics import MapMetrics
from ..resources import BaseFinder
from ..flood import upscale_matrix, summarize_for_greater_scale
from .mocks import PybroodMock
from .render import MapRenderer


def v2(maphash):
    pybrood = PybroodMock(maphash)
    mm = MapMetrics.from_pybrood(pybrood)
    finder = BaseFinder(pybrood.game, mm)

    # wmap = finder.get_walkable_wall_predicate()
    # rnd.draw_walkable_map(lambda x, y: (255 if wmap(x, y) else 0, 0, 0))

    mscores = finder.mineral_scoremap()
    gscores = finder.gas_scoremap()

    mscores = upscale_matrix(finder.build_place_scores(summarize_for_greater_scale(mscores, mm.BWS)), mm.BWS)
    gscores = upscale_matrix(finder.build_place_scores(summarize_for_greater_scale(gscores, mm.BWS)), mm.BWS)

    # unbuildable_area_mask = upscale_matrix(~finder.get_possible_base_locations_mask(), mm.BWS)
    # mscores[unbuildable_area_mask] = 0
    # gscores[unbuildable_area_mask] = 0

    mscores = mscores / mscores.max()
    gscores = gscores / gscores.max()

    rnd = MapRenderer(pybrood.game, mm)
    rnd.draw_walkable_map(lambda x, y: (int(255 * mscores[y, x]), int(255 * gscores[y, x]), 0))
    rnd.im.save('v2.png')

    full_scores = mscores * gscores
    full_scores = full_scores / gscores.max()

    rnd = MapRenderer(pybrood.game, mm)
    rnd.draw_walkable_map(lambda x, y: (int(255 * full_scores[y, x]), int(255 * full_scores[y, x]), 0))
    rnd.im.save('v3.png')
