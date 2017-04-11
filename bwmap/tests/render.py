from PIL import Image, ImageDraw

from ..metrics import MapMetrics
from ..resources import BASE_SIZE


def render_map(game, mm: MapMetrics, valid_bases, output_fname='out.png'):
    w, h = mm.get_map_shape()
    BWS, WS = mm.BWS, mm.WS
    im = Image.new('RGB', (w, h))
    draw = ImageDraw.Draw(im, 'RGBA')
    for y in range(h):
        for x in range(w):
            im.putpixel((x, y), (150, 150, 150) if game.isWalkable(x, y) else (100, 100, 100))

    for y in range(0, h, BWS):
        for x in range(0, w, BWS):
            if not game.isBuildable(x // BWS, y // BWS):
                draw.rectangle((x, y, x + BWS - 1, y + BWS - 1), fill=(0, 0, 0, 40))

    for x, y in game.getStartLocations():
        draw.rectangle((x * BWS, y * BWS, (x + BASE_SIZE[0]) * BWS, (y + BASE_SIZE[1]) * BWS), outline=(200, 200, 40))

    for u in game.getMinerals():
        draw.rectangle((
            u.getLeft() / WS,
            u.getTop() / WS,
            u.getRight() / WS,
            u.getBottom() / WS,
        ), outline=(40, 200, 200))
    for u in game.getGeysers():
        draw.rectangle((
            u.getLeft() / WS,
            u.getTop() / WS,
            u.getRight() / WS,
            u.getBottom() / WS,
        ), outline=(40, 200, 40))

    for y in range(0, h, BWS):
        for x in range(0, w, BWS):
            vb = valid_bases.get((x // BWS, y // BWS))
            if vb is not None:
                draw.rectangle(
                    (x, y, x + BWS * BASE_SIZE[0] - 1, y + BWS * BASE_SIZE[1] - 1),
                    fill=(0, 255, 0, 80)
                )
                cx = (2 * x + BWS * BASE_SIZE[0]) // 2
                cy = (2 * y + BWS * BASE_SIZE[1]) // 2
                for u in vb['resources']:
                    ub = u[0]
                    ux = (ub[0] + ub[1]) // 2
                    uy = (ub[2] + ub[3]) // 2
                    draw.line((cx, cy, ux, uy), fill=(0, 255, 0, 80))
                draw.text((x, y), '{:.0f}'.format(vb['score']), fill=(0, 0, 0))

    im.save(output_fname)
