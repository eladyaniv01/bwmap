import json
from os.path import join

from PIL import Image

from .mocks import DATA_FOLDER


def get_unit_data(u):
    return {
        'id': u.getID(),
        'resources': u.getResources(),
        'left': u.getLeft(),
        'right': u.getRight(),
        'top': u.getTop(),
        'bottom': u.getBottom(),
    }


def save_real_game(game, fname):
    from bakabot.maptools import BWS

    with open(join(DATA_FOLDER, fname + '.json'), 'w') as f:
        json.dump({
            'mapHeight': game.mapHeight(),
            'mapWidth': game.mapWidth(),
            'startLocations': game.getStartLocations(),
            'minerals': [get_unit_data(u) for u in game.getMinerals()],
            'geysers': [get_unit_data(u) for u in game.getGeysers()],
        }, f, indent=2)

    shape = (game.mapWidth() * BWS, game.mapHeight() * BWS)
    im = Image.new('L', shape)
    for y in range(shape[1]):
        for x in range(shape[0]):
            im.putpixel((x, y), 255 if game.isWalkable(x, y) else 0)
    im.save(join(DATA_FOLDER, fname + '_walk.png'))

    shape = (game.mapWidth(), game.mapHeight())
    im_build = Image.new('L', shape)
    im_height = Image.new('RGB', shape)
    heights = {
        0: (0, 255, 0),
        1: (0, 127, 0),
        2: (255, 255, 0),
        3: (127, 127, 0),
        4: (255, 0, 0),
        5: (127, 0, 0),
    }
    for y in range(shape[1]):
        for x in range(shape[0]):
            im_build.putpixel((x, y), 255 if game.isBuildable(x, y) else 0)
            im_height.putpixel((x, y), heights[game.getGroundHeight(x, y)])
    im_build.save(join(DATA_FOLDER, fname + '_build.png'))
    im_height.save(join(DATA_FOLDER, fname + '_height.png'))


def save_map_from_bwapi():
    from pybrood import run, game, BaseAI

    class SaveMapAI(BaseAI):
        def prepare(self):
            save_real_game(game, game.mapHash())
            print('Map {} saved'.format(game.mapHash()))

        def frame(self):
            game.leaveGame()

    run(SaveMapAI, once=True)
