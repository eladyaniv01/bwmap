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
