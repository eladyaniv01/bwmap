from PIL import Image, ImageDraw

from ..metrics import MapMetrics
from ..resources import BaseFinder
from ..flood import upscale_matrix, summarize_for_greater_scale
from ..choke import ChokeFinder, SameSideNodeMerger
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


def chokes(maphash):
    pybrood = PybroodMock(maphash)
    mm = MapMetrics.from_pybrood(pybrood)
    finder = ChokeFinder(pybrood.game, mm)

    finder()

    PX_SIZE = 4

    walkmap = mm.get_walkability_map()

    im = Image.new('RGB', tuple(x * PX_SIZE for x in walkmap.shape))
    draw = ImageDraw.Draw(im, 'RGBA')
    for y in range(walkmap.shape[0]):
        for x in range(walkmap.shape[1]):
            color = (200, 200, 200) if walkmap[y, x] else (100, 100, 100)
            draw.rectangle((x * PX_SIZE, y * PX_SIZE, (x + 1) * PX_SIZE, (y + 1) * PX_SIZE), fill=color)

    merger = SameSideNodeMerger(finder.iter_nodes())
    merger()

    for x, y, szx, szy in merger:
        draw.rectangle((x * PX_SIZE, y * PX_SIZE, (x + szx) * PX_SIZE, (y + szy) * PX_SIZE), outline=(0, 0, 0))

    im.save('choke.png')
