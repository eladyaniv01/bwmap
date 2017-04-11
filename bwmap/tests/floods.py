from ..metrics import MapMetrics
from ..resources import BaseFinder
from .mocks import PybroodMock
from .render import MapRenderer


def v2(maphash):
    pybrood = PybroodMock(maphash)
    mm = MapMetrics.from_pybrood(pybrood)
    finder = BaseFinder(pybrood.game, mm)
    rnd = MapRenderer(pybrood.game, mm)

    # wmap = finder.get_walkable_wall_predicate()
    # rnd.draw_walkable_map(lambda x, y: (255 if wmap(x, y) else 0, 0, 0))

    mscores = finder.mineral_scoremap()
    mscores = mscores / mscores.max()
    gscores = finder.gas_scoremap()
    gscores = gscores / gscores.max()
    rnd.draw_walkable_map(lambda x, y: (int(255 * mscores[y, x]), int(255 * gscores[y, x]), 0))

    rnd.im.save('v2.png')
