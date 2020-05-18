# Swishulator

An emulator/simulator that reads plist level files from the popular competitive golf game QUATRO. It allows to simulate -using the pymunk 2d physics engine- regular shots and different powerups and scan a range of 180 degrees for the best possible shot with a given velocity, often with hilarious results. 

Most parameters of the actual game are unknown and/or unrelated to physical units (such as the mysterious NoodleNewton). Feel free to experiment and optimize these.

![Magnet 8 - Swish](/examples/mag8.png)

## requirements

 * python3, and some libraries: numpy, json, contextlib, base64
 * python3-pymunk, the chipmunk 2d physics engine for python
 * plist level files. 

## usage:

```
usage: ./sim.py [-h] [-a [ANGLE]] [-m [MODE]] [-n [NEWTON]] [-p [POWER]] [-u [POWERUP]] [-s [SPREAD]] [-z [ZOOM]] [-d [DELAY]] level

positional arguments:
  level                 plist file to read and run the simulation in

optional arguments:
  -h, --help            show this help message and exit
  -a [ANGLE], --angle [ANGLE]
                        angle of the shot/starting angle of the simulation
  -m [MODE], --mode [MODE]
                        simulation mode [headless, show, (sim, spread)]
  -n [NEWTON], --newton [NEWTON]
                        ball power (NoodleNewton)
  -p [POWER], --power [POWER]
                        ball power (P1-13)
  -u [POWERUP], --powerup [POWERUP]
                        powerup selection [regular, heavy, shield, antigrav, sticky]
  -s [SPREAD], --spread [SPREAD]
                        spread range to simulate in spread mode
  -z [ZOOM], --zoom [ZOOM]
                        change the zoom factor if your screen is too large/small
  -d [DELAY], --delay [DELAY]
                        wait d seconds until taking your shot
```

where:
 * **level.plist** is a level file 
 * **angle** is the angle to simulate, or in scanning mode the angle to start scanning with, in degrees. 
 * **mode**: one of 
   * **show**: simulate a shot, don't erase - useful for screenshots
   * **sim**: simulate a shot, increase the angle, continue
   * **headless**: as 'sim', but don't update the display, to quickly scan for the best shots and swishes
   * **spread**: simulate a range of angles, don't erase - useful for screenshots and showing where different shots end up. The next parameter should be the angle spread.
 * **newton** is the power to simulate, in approximated NoodleNewton[1]
 * **power** alternatively you can specify the player's power skill level in the range 1-13 (12 for powerups). This will override the Newton setting.
 * **powerup**: one of
   * **heavy**: remove ball elasticity. 
   * **antigrav**: reverse gravity
   * **shield**: change saws and acid into regular obstacles, allow one bounce on water
   * **sticky**: stop calculations at the first obstacle hit
 * **spread**: the angle spread, if spread mode is selected 
 * **zoom**: scale the output windows. Since the window is pretty large already, float numbers below 1.0 are most sensible.
 * **delay**: simulate the initial countdown to ensure movers are in the right position.
 
## examples:

`./sim.py level0.plist`

tries to find the best shot off tee in this level using the default settings (Power 13/40NN), angle 0-180 in steps of 0.1, regular ball, HEADLESS mode (scanning). A black window will open while the engine is scanning through 1800 possible angles. When finished, it will display possible swishes, the best angle, and the best angle for various spreads. Finally, a new window will pop up simulating the best angle in SHOW mode.

`./sim.py level0.plist -a 45 -n 30 -m show`

simulates a single shot with angle 45, power 30 NN. 

`./sim.py level0.plist -n 41.1 -m headless -u shield` 

tries to find the best shot using shield ball. Here, we explicitly specify the starting angle (which is increased in steps of 0.1), power in NoodleNewton, headless mode and powerup.

## settings:

A number of constants can be set at the beginning of the simulation script. Please check the section `VARIABLES WE NEED TO EYEBALL`.

They are set to somewhat sensible defaults, but there is almost as much room for improvement. 

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
