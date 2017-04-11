import json
from os.path import join

from PIL import Image


DATA_FOLDER = 'data'


class UnitMock:
    def __init__(self, data):
        self.data = data

    def getID(self):
        return self.data['id']

    def getResources(self):
        return self.data['resources']

    def getLeft(self):
        return self.data['left']

    def getRight(self):
        return self.data['right']

    def getTop(self):
        return self.data['top']

    def getBottom(self):
        return self.data['bottom']


class GameMock:
    def __init__(self, fname):
        with open(join(DATA_FOLDER, fname + '.json')) as f:
            self.data = json.load(f)
        self.walkable = Image.open(join(DATA_FOLDER, fname + '_walk.png'))
        self.buildable = Image.open(join(DATA_FOLDER, fname + '_build.png'))
        self.slocs = tuple(self.data['startLocations'])
        self.minerals = tuple(UnitMock(u) for u in self.data['minerals'])
        self.geysers = tuple(UnitMock(u) for u in self.data['geysers'])

    def mapHeight(self):
        return self.data['mapHeight']

    def mapWidth(self):
        return self.data['mapWidth']

    def isWalkable(self, x, y):
        return self.walkable.getpixel((x, y)) > 0

    def isBuildable(self, x, y):
        return self.buildable.getpixel((x, y)) > 0

    def getStartLocations(self):
        return self.slocs

    def getMinerals(self):
        return self.minerals

    def getGeysers(self):
        return self.geysers


class PybroodMock:
    WALKPOSITION_SCALE = 8
    TILEPOSITION_SCALE = 32

    def __init__(self, map_hash):
        self.game = GameMock(map_hash)

    # m.game = GameMock('ac00190eb40d77eaf0dbf9e6a1030f4eb5229e7d')
    # m.game = GameMock('b48cd49f154e3ecc5ec4af83566a6f02480e95f2')  # Lost Temple
    # m.game = GameMock('fb98f70052bd29c0cfea343cf9608a5790a21d8b')  # big game hunters
    # m.game = GameMock('a8c292c60ed1bd10c57d2e794e1109904a3fadda')  # hunters x4

    # from bakabot.base_places import find_bases
    # from maptest.render import render_map
    # render_map(find_bases())
