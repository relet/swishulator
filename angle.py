#!/usr/bin/env python3

import json 
import math
import numpy
import os
import sys
import time

# how to determine: `adb shell wm size` - centerx is half of the override size
CENTERX = 360
# how to determine: do a slow horizontal swipe. if the ball cursor doesn't bounce up or down from this position, you are pixel perfect
CENTERY = 1073 
RADIUS = 400
# swipe speed in ms - this is the minimum we managed
SPEED = 100

try:
    angle = float(sys.argv[1])
except Exception as x:
  print(x)
  sys.exit(1)

if angle is None:
     # TODO: try and get a different power level
     print("No swipe possible")
     sys.exit(1)

r = RADIUS 

rx = r * math.cos(numpy.deg2rad(angle)) 
ry = r * math.sin(numpy.deg2rad(angle))

print("BEST ANGLE {}".format(angle))
print("adb shell input touchscreen swipe {} {} {} {} {}".format(CENTERX, CENTERY, CENTERX-rx, CENTERY+ry, SPEED))
input()
os.system("adb shell input touchscreen swipe {} {} {} {} {}".format(CENTERX, CENTERY, CENTERX-rx, CENTERY+ry, SPEED))
