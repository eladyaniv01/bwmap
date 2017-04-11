import click


@click.group(help='Commands marked with (LIVE) require SC launch and windows environment.')
def bwmap():
    pass


@bwmap.command(help='(LIVE) Make data snapshot for map, which can be used in mock objects later')
def snapshot():
    from .tests.snapshot import save_map_from_bwapi
    save_map_from_bwapi()


@bwmap.command(help='(LIVE) Check map buildtiles')
def buildable_test():
    from .tests.buildable import detect_bads
    detect_bads()


@bwmap.command(help='Make better output for buildable_test result')
def buildable_refine():
    from .mapanalyzer.tests.buildable import refine
    refine('output.txt')


@bwmap.command(help='Find & render best places for bases using map snapshot')
@click.argument('maphash')
def findbases(maphash):
    from .resources import BaseFinder
    from .metrics import MapMetrics
    from .tests.mocks import PybroodMock
    from .tests.render import render_map

    pybrood = PybroodMock(maphash)
    mm = MapMetrics.from_pybrood(pybrood)
    valid_bases = BaseFinder(pybrood.game, mm)()
    render_map(pybrood.game, mm, valid_bases)


@bwmap.command(help='Find & render v2')
@click.argument('maphash')
def findbases2(maphash):
    from .tests.flood import v2

    v2(maphash)


if __name__ == '__main__':
    bwmap(prog_name='python -m bwmap')
