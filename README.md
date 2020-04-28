# Swishulator

An emulator/simulator that reads plist level files from the popular competitive golf game QUATRO. It allows to simulate -using the pymunk 2d physics engine- regular shots and different powerups and scan a range of 180 degrees for the best possible shot with a given velocity, often with hilarious results. 

Most parameters of the actual game are unknown and/or unrelated to physical units (such as the mysterious NoodleNewton). Feel free to experiment and optimize these.

![Magnet 8 - Swish](/examples/mag8.png)

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

## screen sizes

The simulator doesn't scroll along with the ball, so some levels are just too big for your screen. It is also currently configured for a rather large screen estate. The lines you can change are

`SCALE = 1` - scales (hopefully) all elements in the game
`window = (x,y)` - changes the size of the displayed window
`screen_center = (x,y)` - pans the entire level. 

If your screen just stays blank (except in headless mode, where it is supposed to be blank), try changing the SCALE, then changing the center. You might just be looking at the wrong portion of the level. Only if the game window is larger than your physical screen, reduce that. 

## known issues:

 * The ball might bounce in the wrong direction at corners where two segments meet. The issue seems to be that he penetrates too deep so that he first hits the side of the angled segment instead of the face of the closer segment. Decreasing the step size might help. 
 * In general, all parameters are eyeballed - ball velocity and elasticity might be a bit on the high side.
 * Portal code is work in progress. Some settings work in some levels and fail in others. 
 * Rotating sticky and acid are not yet correctly simulated. Moving sticky and acid is. 
 * Some movers and platforms are not yet correctly placed or scaled.
 * Kinematic objects should in theory be moved by changing their velocity, but I haven't managed to make that work yet. Hence the ball can pass through fast moving movers. 
 * Visuals are just the pymunk debug mode. It is mostly a simulation engine.
 * In particular sticky and acid masks are not moved/rotated. 
 * ... etc pp. Code flows around what works and what not. It's only an issue if it doesn't work for the level you are currently trying to simulate, eh? 
