import json


def detect_bads():
    import pybrood
    from pybrood import game, BaseAI, run
    from ..metrics import MapMetrics

    mm = MapMetrics.from_pybrood(pybrood)
    BWS = mm.BWS

    class NotWalkable(Exception):
        pass

    class LiveTestAI(BaseAI):
        def prepare(self):
            print('Map {} {}'.format(game.mapFileName(), game.mapHash()))
            shape = (game.mapWidth(), game.mapHeight())
            self.failed_tiles = []
            for y in range(shape[1]):
                for x in range(shape[0]):
                    if not game.isBuildable(x, y):
                        continue
                    try:
                        for wy in range(y * BWS, (y + 1) * BWS):
                            for wx in range(x * BWS, (x + 1) * BWS):
                                if not game.isWalkable(wx, wy):
                                    raise NotWalkable
                    except NotWalkable:
                        self.failed_tiles.append((x, y))
            with open('output.txt', 'a') as f:
                f.write('#########\n')
                f.write(json.dumps({
                    'hash': game.mapHash(),
                    'pathname': game.mapPathName(),
                    'filename': game.mapFileName(),
                    'failed_tiles': self.failed_tiles,
                }) + '\n')
            print(self.failed_tiles)

        def frame(self):
            game.leaveGame()

    run(LiveTestAI)


def split_to_well_sized_lines(items, max_len, sep):
    result = []
    stack, stack_len = [], 0

    def flush():
        nonlocal stack_len
        if stack:
            result.append(sep.join(stack))
        stack.clear()
        stack_len = 0

    for item in items:
        if stack_len and stack_len + len(sep) + len(item) > max_len:
            flush()
        stack.append(item)
        stack_len += (len(sep) if stack_len else 0) + len(item)
    flush()
    return result


def refine(fname):
    items = []
    with open(fname) as f:
        for item in f.read().split('#########'):
            item = item.strip()
            if not item:
                continue
            items.append(json.loads(item))
    for item in items:
        if item['failed_tiles']:
            print(item['pathname'])
            lines = split_to_well_sized_lines([
                json.dumps(ft) for ft in item['failed_tiles']
            ], 80, ', ')
            for line in lines:
                print('  {}'.format(line))
