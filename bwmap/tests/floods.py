from ..metrics import MapMetrics
from .mocks import PybroodMock
from .render import MapRenderer


def v2(maphash):
    pybrood = PybroodMock(maphash)
    mm = MapMetrics.from_pybrood(pybrood)

    rnd = MapRenderer(pybrood.game, mm)
