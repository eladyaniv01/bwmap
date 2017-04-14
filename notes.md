max map size:

256*256 build tiles (TilePosition)
1024*1024 walk tiles (WalkPosition)
8192*8192 pixels (Position)


Don't import `pybrood` at module levels where possible.
Better require `pybrood.game` as parameter.


## TODO

#### Find places for resource bases

- ✓ make buildtile mask (including resource unit masks + 3 gap)
- ✓ merge calculated rates on walk tiles into build tiles
- ✓ calculate sums for resource depot size (4*3) for each build tile
  considering coordinates as topleft corner of depot
- ✓ find extremums and place base locations
- ✓ find all resources possessed by particular base location
  (using same wave tracing from base location with limited distance)
- ✓ decouple map analyzing code for ability to test
- make ability to place additional bases for same resources to speed up mining
- optimize whole thing


gather_time + unload_time + 2 * walk_time
C_time = gather_time + unload_time
res_per_second = res_per_walk / (C_time + 2 * walk_time)



3.7 / (5.5 - 3.7) = C_time / (2 * walk_time)
0.9 = walk_time (3 tiles)
speed = 3 / 0.9 = 3.333 tiles per t
res_per_second = 8 / (3.7 + 2 / 3.333 * dist) = 8 / (3.7 + 0.6 * dist)


http://starcraft.wikia.com/wiki/Crystallis


3.7 3.8 - mining
4.8 4.7 - reaching base
6.3 6.3 - returned to patch

distance = 3 build tiles

~3.7 seconds to mine
~1 second to go over 3 tiles
~0.6 seconds to unload resource
~1 second to go over 3 tiles

res_per_second = res_per_walk / (gather_time + unload_time + 2 * walk_time)
res_per_second = 8 / (3.7 + 0.6 + 2 * 1) = 1.27 (76 per minute)
walk_time = distance / speed
1 = 3 / speed
speed = 3 / 1 = 3
res_per_second = 8 / (3.7 + 0.6 + 2 * (distance / 3))
res_per_second = 8 / (4.3 + 0.67 * distance))

res_per_second(120 tiles) = 0.094 (5.6 per minute)
