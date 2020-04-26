# Swishulator

An emulator/simulator that reads plist level files from the popular competitive golf game QUATRO. It allows to simulate -using the pymunk 2d physics engine- regular shots and different powerups and scan a range of 180 degrees for the best possible shot with a given velocity, often with hilarious results. 

Most parameters of the actual game are unknown and/or unrelated to physical units (such as the mysterious NoodleNewton). Feel free to experiment and optimize these.

## requirements

 * python3, and some libraries: numpy, json, contextlib, base64
 * python3-pymunk, the chipmunk 2d physics engine for python
 * plist level files. 

## usage:

`./sim.py level.plist [angle] [power] [mode] [powerup|spread]`

where:
 * **level.plist** is a level file 
 * **angle** is the angle to simulate, or in scanning mode the angle to start scanning with, in degrees. 
 * **power** is the power to simulate, in approximated NoodleNewton[1]
 * **mode**: one of 
   * **show**: simulate a shot, don't erase - useful for screenshots
   * **sim**: simulate a shot, increase the angle, continue
   * **headless**: as 'sim', but don't update the display, to quickly scan for the best shots and swishes
   * **spread**: simulate a range of angles, don't erase - useful for screenshots and showing where different shots end up. The next parameter should be the angle spread.
 * **spread**: the angle spread, if spread mode is selected 
 * **powerup**: one of
   * **heavy**: remove ball elasticity. 
   * **antigrav**: reverse gravity
   * **shield**: change saws and acid into regular obstacles, allow one bounce on water
 
 [1] This is somewhat calibrated for around 36.4-40N. I am not sure how linear the scale is, so currently lower values fall short of the mark, while power ball shots overshoot.
 
## settings:

A number of constants can be set at the beginning of the simulation script. Please check the section `VARIABLES WE NEED TO EYEBALL`.

They are set to somewhat sensible defaults, but there is almost as much room for improvement. 

## known issues:

 * In general, all parameters are eyeballed - ball velocity and elasticity might be a bit on the high side.
 * Portal code is work in progress. Some settings work in some levels and fail in others. 
 * Rotating sticky and acid are not yet correctly simulated. Moving sticky and acid is. 
 * Some movers and platforms are not yet correctly placed or scaled.
 * Kinematic objects should in theory be moved by changing their velocity, but I haven't managed to make that work yet. Hence the ball can pass through fast moving movers. 
 * Visuals are just the pymunk debug mode. It is mostly a simulation engine.
 * In particular sticky and acid masks are not moved/rotated. 
 * ... etc pp. Code flows around what works and what not. It's only an issue if it doesn't work for the level you are currently trying to simulate, eh? 