from PIL import Image, ImageDraw

from ..metrics import MapMetrics
from ..resources import BASE_SIZE


class MapRenderer:
    def __init__(self, game, mm: MapMetrics):
        self.game = game
        self.mm = mm
        self.im = Image.new('RGB', self.wh)
        self.draw = ImageDraw.Draw(self.im, 'RGBA')

    @property
    def wh(self):
        return self.mm.get_map_shape(scale=self.mm.WS)

    def draw_walkable_tile(self, x, y, color):
        self.draw.point((x, y), fill=color)

    def draw_buildable_tile(self, x, y, color):
        BWS = self.mm.BWS
        x, y = x * BWS, y * BWS
        self.draw.rectangle((x, y, x + BWS - 1, y + BWS - 1), fill=color)

    def draw_walkable_rect(self, x, y, w, h, **kw):
        self.draw.rectangle((x, y, x + w, y + h), **kw)

    def draw_buildable_rect(self, x, y, w, h, **kw):
        BWS = self.mm.BWS
        self.draw.rectangle((x * BWS, y * BWS, (x + w) * BWS, (y + h) * BWS), **kw)

    def draw_unit_outline(self, u, color):
        WS = self.mm.WS
        self.draw_walkable_rect(
            u.getLeft() / WS,
            u.getTop() / WS,
            (u.getRight() - u.getLeft()) / WS,
            (u.getBottom() - u.getTop()) / WS,
            outline=color
        )

    def draw_walkable_map(self, color_func):
        w, h = self.wh
        for y in range(h):
            for x in range(w):
                color = color_func(x, y)
                if color is not None:
                    self.draw_walkable_tile(x, y, color)

    def draw_buildable_map(self, color_func):
        w, h = self.mm.get_map_shape(scale=self.mm.BS)
        for y in range(h):
            for x in range(w):
                color = color_func(x, y)
                if color is not None:
                    self.draw_buildable_tile(x, y, color)

    def walkable_color(self, wall, space):
        return lambda x, y: space if self.game.isWalkable(x, y) else wall

    def buildable_color(self, wall, space):
        return lambda x, y: space if self.game.isBuildable(x, y) else wall


def render_map(game, mm: MapMetrics, valid_bases, output_fname='out.png'):
    rnd = MapRenderer(game, mm)
    rnd.draw_walkable_map(rnd.walkable_color((100, 100, 100), (150, 150, 150)))
    rnd.draw_buildable_map(rnd.buildable_color((0, 0, 0, 40), None))

    for x, y in game.getStartLocations():
        rnd.draw_buildable_rect(x, y, *BASE_SIZE, outline=(200, 200, 40))

    for u in game.getMinerals():
        rnd.draw_unit_outline(u, (40, 200, 200))
    for u in game.getGeysers():
        rnd.draw_unit_outline(u, (40, 200, 40))

    for (x, y), vb in valid_bases.items():
        rnd.draw_buildable_rect(x, y, *BASE_SIZE, fill=(0, 255, 0, 80))
        cx = (2 * x + BASE_SIZE[0]) * mm.BWS // 2
        cy = (2 * y + BASE_SIZE[1]) * mm.BWS // 2
        for u in vb['resources']:
            ub = u[0]
            ux = (ub[0] + ub[1]) // 2
            uy = (ub[2] + ub[3]) // 2
            rnd.draw.line((cx, cy, ux, uy), fill=(0, 255, 0, 80))
        rnd.draw.text((x * mm.BWS, y * mm.BWS), '{:.0f}'.format(vb['score']), fill=(0, 0, 0))

    rnd.im.save(output_fname)
