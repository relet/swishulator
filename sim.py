#!/usr/bin/env python3

import argparse
import base64
import contextlib
import json
import math
import numpy
import os
import re
import sys
import time

with contextlib.redirect_stdout(None):
    import pygame
    import pymunk
    import pymunk.pygame_util
    from pymunk.vec2d import Vec2d

# CONSTANTS
# collision types

collision_types = {
        "wall": 9, #default
        "ball": 1,
        "sand": 2,
        "water": 3,
        "antigrav": 4,
        "magnet": 5,
        "portal": 6,
        "laser": 7,
        "lasersensor": 8
        }

SKILLS = {
        'regular':[25,25.7,26.5,27.4,28.4,29.5,30.7,32.1,33.6,35.3,37.1,39,41.1],
        'maxp12':[25,25.7,26.5,27.4,28.4,29.5,30.7,32.1,33.6,35.3,37.1,39,39],
        'super':[54.1,55.8,57.7,60,62.4,65.2,68.3,71.7,75.5,79.6,84.1,89,89],
        'heavy':[17.4,17.8,18.3,18.9,19.5,20.2,21,21.8,22.8,23.8,24.9,26.1,26.1],
        'saw':[29.9,30.7,31.5,32.5,33.6,34.8,36.2,37.7,39.3,41.1,43,45.1,45.1]
        }
SKILLS['sticky']=SKILLS['maxp12']
SKILLS['shield']=SKILLS['maxp12']
SKILLS['tunnel']=SKILLS['maxp12']


# simulation modes

MODE_SIM  = 0
MODE_SHOW = 1
MODE_HEADLESS = 2
MODE_SPREAD = 3

SUBMODE_NORMAL = 0
SUBMODE_HEAVY = 1
SUBMODE_SHIELD = 2
SUBMODE_ANTIGRAV = 3
SUBMODE_STICKY = 4
SUBMODE_TUNNEL = 5

#VARIABLES WE NEED TO EYEBALL

TERRAIN_ELASTICITY = 0.6
SIDEWALL_ELASTICITY = 0.6
TERRAIN_FRICTION = 0.5
SEGMENT_THICKNESS = 2

BALL_MASS = 1.0
BALL_MOMENT = 13.5
BALL_RADIUS = 5.0
BALL_ELASTICITY = 0.6
BALL_FRICTION = 0.7

# distance the ball has to travel before switching status (tunnel, sticky, ghost)
GHOST_DISTANCE = 15

POWER_FACTOR = 1.35109
POWER_BASELINE = 39
TIME_FACTOR = 0.3333


window = (3200,4800)
WIDTH,HEIGHT = window

# defaults(some are overridden in argparse below) 
power = 41.1
init_angle = 0
mode = MODE_HEADLESS
submode = SUBMODE_NORMAL

# reading command line arguments

parser = argparse.ArgumentParser('./sim.py')
parser.add_argument('level', type=str, help='plist file to read and run the simulation in', nargs=1)
parser.add_argument('-a', '--angle', type=float, help='angle of the shot/starting angle of the simulation', nargs='?', default=0.0)
parser.add_argument('-m', '--mode', type=str, help='simulation mode [headless, show, (sim, spread)]', nargs='?', default='headless')
parser.add_argument('-n', '--newton', type=float, help='ball power (NoodleNewton)', nargs='?', default=None)
parser.add_argument('-p', '--power', type=int, help='ball power (P1-13)', nargs='?', default=13)
parser.add_argument('-u', '--powerup', type=str, help='powerup selection [regular, heavy, shield, antigrav, sticky, tunnel, super]', nargs='?', default='regular')
parser.add_argument('-s', '--spread', type=float, help='spread range to simulate in spread mode', nargs='?', default=3.5)
parser.add_argument('-z', '--zoom', type=float, help='change the zoom factor if your screen is too large/small', nargs='?', default=1.0)
parser.add_argument('-d', '--delay', type=float, help='wait d seconds until taking your shot', nargs='?', default=3.05)
parser.add_argument('-t', '--target', type=str, help='optimization target (distance, high, low, left, right)', nargs='?', default='distance')
parser.add_argument('-v', '--vertical', type=int, help='shift the viewport by this many pixels, vertically', nargs='?', default='0')
parser.add_argument('--ignore-sticky', dest="ignore_sticky", help='ignore sticky masks', action='store_true')
args = parser.parse_args()

print(args)

screen_center = (0,2500+args.vertical)

if args.mode:
    if args.mode=="headless":
        mode = MODE_HEADLESS
    elif args.mode=="sim":
        mode = MODE_SIM
    elif args.mode=="spread":
        mode = MODE_SPREAD
    elif args.mode=="show":
        mode = MODE_SHOW

if args.newton:
    power = args.newton

target = args.target

if args.powerup:
    if args.powerup == "heavy":
        BALL_ELASTICITY = 0
        TERRAIN_ELASTICITY = 0
        submode = SUBMODE_HEAVY
    elif args.powerup == "shield":
        submode = SUBMODE_SHIELD
    elif args.powerup == "antigrav":
        submode = SUBMODE_ANTIGRAV
    elif args.powerup == "sticky":
        submode = SUBMODE_STICKY
    elif args.powerup == "tunnel":
        submode = SUBMODE_TUNNEL

if args.spread:
    spread = args.spread

if args.power and not args.newton:
    power = SKILLS[args.powerup][args.power-1] 

if args.angle:
    init_angle = args.angle #archangel? 

angle = init_angle

WAIT = args.delay # wait until starting.

# LOAD TERRAIN FILE

try:
    data=json.load(open(args.level[0],"r"))
except Exception as ex:
    print(ex)
    sys.exit(1)

# UTILITY METHODS

def loads_coord(s):
    """load strange serialized coord lists {1,2,3...}"""
    return json.loads(s.replace('{','[').replace('}',']'))

# stupid 2d vector calculation, you could probably use numpy methods and Vec2d instead.

def plus(a,b):
    return [sum(x) for x in zip(a,b)]

def scale(p,s):
    sx,sy = s
    px,py = p
    return (px*sx, py*sy)

def neg(a):
    return [-x for x in a]

def make_square(c):
    x1,y1 = c[0]
    x2,y2 = c[1]
    return [(x1,y1),(x1,y2),(x2,y2),(x2,y1),(x1,y1)]

def distance(x1,x2,y1,y2):
    dx = x2-x1
    dy = y2-y1
    return math.sqrt(dx*dx+dy*dy)


# PARAMETERS FROM DATA FILE

nodes = data['nodes']
top = loads_coord(nodes[0]['position'])[1]
right = loads_coord(nodes[1]['position'])[0]
right,top = plus((right,top), screen_center)

gravity = float(data['gravity']) 

# PHYSICS

space = pymunk.Space()
if submode == SUBMODE_ANTIGRAV:
    space.gravity = (0,gravity)
else:
    space.gravity = (0,-gravity)
static = space.static_body

bodies = {}
portals = {}
rotations = {}
translations = {}
masks = []
stickies = {}
acids = {}
lasers = {}
fields = []
magnets = []

# LAYERS

solid_filter = pymunk.ShapeFilter(categories=0x01)
pass_filter = pymunk.ShapeFilter(categories=0x02)

bbox = make_square(((0,2500),(right,top)))

body = pymunk.Body(body_type = pymunk.Body.STATIC)
body.id_ = "bbox"
body.reset_position = body.position
bodies['bbox']=body
#left wall
segment = pymunk.Segment(body, bbox[0], bbox[1], SEGMENT_THICKNESS)
segment.elasticity = SIDEWALL_ELASTICITY
segment.friction = TERRAIN_FRICTION
segment.color=(150,40,40)
space.add(segment)
#right wall
segment = pymunk.Segment(body, bbox[2], bbox[3], SEGMENT_THICKNESS)
segment.elasticity = SIDEWALL_ELASTICITY
segment.friction = TERRAIN_FRICTION
segment.color=(150,40,40)
space.add(segment)

for node in nodes:
    id_ = node['id']
    pos = loads_coord(node['position'])
    pos = plus (pos, screen_center)
    type_ = node['type']
    width = float(node.get('width',0))
    height = float(node.get('height',0))

    rotate = node.get('rotation-actions')
    translate = node.get('position-actions')

    shapes = None
    if type_ == 'TerrainNode' and node['collisionsEnabled'] != "0":
        shapes = node['vertices-processed']
        rotation = loads_coord(node['node-rotation'])

        offset = loads_coord(node['terrain-offset'])
        center = (width/2.0, height/2.0)

        body = pymunk.Body(body_type = pymunk.Body.KINEMATIC)
        body.position = pos
        body.reset_position = pos

        for shape in shapes:
            loaded = [plus(loads_coord(v), neg(center)) for v in shape]
            loaded.append(loaded[0])
            for i in range(len(loaded)-1):
                segment = pymunk.Segment(body, loaded[i], loaded[i+1], SEGMENT_THICKNESS)
                segment.elasticity = TERRAIN_ELASTICITY
                segment.friction = TERRAIN_FRICTION
                segment.filter = solid_filter
                segment.collision_type = collision_types['wall']
                segment.color=(80,200,80)
                if rotate or translate:
                    segment.color=(20,60,20)
                space.add(segment)

        body.angle = numpy.deg2rad(-rotation)
        body.reset_angle = body.angle
        body.id_ = id_
        bodies[id_] = body

    if type_ == 'GravityFieldNode':
        pos = loads_coord(node['position'])
        node_anchor = loads_coord(node['node-anchor'])
        size = loads_coord(node['size'])
        strength = loads_coord(node['strength'])
        dir_ = loads_coord(node['dir'])
        rotation = loads_coord(node['node-rotation'])

        #TODO FIXME: relative anchor is correct, position is not when anchor>0
        center = (size[0]/2.0, size[1]/2.0)
        anchored = (-size[0]*node_anchor[0], -size[1]*node_anchor[1])
        pos = plus(pos, screen_center)
        loaded = make_square((neg(center),center))

        body = pymunk.Body(body_type = pymunk.Body.KINEMATIC)
        body.center_of_gravity = neg(plus(center,anchored))
        body.position = pos
        body.reset_position = body.position
        segment = pymunk.Poly(body, loaded[:4], radius=SEGMENT_THICKNESS)
        segment.color=(80,80,200)
        segment.filter = pass_filter
        segment.collision_type = collision_types['antigrav']
        segment.sensor = True
        segment.antigrav_dir = dir_
        segment.antigrav_strength = strength
        segment.antigrav_rotation = numpy.deg2rad(rotation)
        space.add(segment)

        body.angle = numpy.deg2rad(-rotation)
        body.reset_angle = body.angle
        bodies[id_] = body

    for r in rotate:
        sequence = rotations.get(id_,{"steps":[]})
        rtype = r['type'] # Cool game
        period = float(r['period'])
        step = {"type": rtype,
                "period": period}
        sequence['duration'] = sequence.get('duration',0.0) + period 
        if rtype=='delay-rotation':
            # just append the duration to step, do nothing
            pass 
        elif rtype=='rotate':
            step['rotation-rate'] = float(r['rotation-rate'])
            #interpolate-mode?
        else:
            print ("UNKNOWN ROTATION ACTION",rtype)
            sys.exit(1)
        sequence['steps'].append(step)
        rotations[id_]=sequence

    old = (0,0)
    for t in translate:
        sequence = translations.get(id_,{"steps":[]})
        ttype = t['type']
        period = float(t['period'])
        sequence['duration'] = sequence.get('duration',0.0) + period 
        step = {"type": ttype,
                "period": period}
        if ttype == 'position':
            rel = loads_coord(t['move-position'])
            step['move-position'] = (rel[0]-old[0], rel[1]-old[1])
            old = rel
            #interpolate-mode?
        elif ttype == 'delay-position':
            pass
        else:
            print ("UNKNOWN POSITION ACTION",ttype)
            sys.exit(1)
        sequence['steps'].append(step)
        translations[id_]=sequence


    acid = node.get('texture-acid-mask')
    if acid:
        do_acid = {
                'id': id_+'_acid',
                'type': 'acid',
                'width':  int(width),
                'height': int(height),
                #VERTICAL axis is inverted, we have to go back from window size
                'pos': (int(pos[0]-width/2), int(window[1]-pos[1]-height/2))
                }
        fd = open('tmp/'+id_+'_acid.png','wb')
        fd.write(base64.b64decode(acid))
        fd.close()
        acids[id_]=do_acid
        masks.append(do_acid)

    sticky = node.get('texture-sticky-mask')
    if sticky and not args.ignore_sticky:
        do_sticky = {
                'id': id_+'_sticky',
                'type': 'sticky',
                'width':  int(width),
                'height': int(height),
                #VERTICAL axis is inverted, we have to go back from window size
                'pos': (int(pos[0]-width/2), int(window[1]-pos[1]-height/2))
                }
        fd = open('tmp/'+id_+'_sticky.png','wb')
        fd.write(base64.b64decode(sticky))
        fd.close()
        masks.append(do_sticky)
        stickies[id_]=do_sticky

    if type_ == 'SandTrapNode':
        if not node.get('hazard-lines'):
            continue
        loaded = loads_coord(node['hazard-lines'][0])
        loaded = make_square(loaded)

        for i in range(len(loaded)-1):
            p0 = plus(pos,loaded[i])
            p1 = plus(pos,loaded[i+1])
            segment = pymunk.Segment(static, p0, p1, SEGMENT_THICKNESS)
            segment.elasticity = 999
            segment.friction = 999
            segment.color=(200,200,40)
            segment.filter = solid_filter
            segment.collision_type = collision_types['sand']
            space.add(segment)

    if type_ == 'WaterHazardNode':
        loaded = loads_coord(node['hazard-lines'][0])
        loaded = make_square(loaded)

        for i in range(len(loaded)-1):
            p0 = plus(pos,loaded[i])
            p1 = plus(pos,loaded[i+1])
            segment = pymunk.Segment(static, p0, p1, SEGMENT_THICKNESS)
            segment.elasticity = 1.5 #TODO: how bouncy? 
            segment.friction = TERRAIN_FRICTION
            segment.color=(40,40,150)
            segment.collision_type = collision_types['water']
            space.add(segment)

    if type_ == 'MagnetNode':
        body = pymunk.Body(body_type = pymunk.Body.KINEMATIC)
        radius = loads_coord(node['radius'])
        strength = loads_coord(node['strength'])
        magnet = pymunk.Circle(body, radius, pos)
        magnet.filter = pass_filter
        magnet.sensor = True
        magnet.color = (200, 200, 200, 50)
        magnet.collision_type = collision_types['magnet']
        magnets.append((pos, radius, strength))
        space.add(magnet)

    if type_ == 'KillSawNode':
        body = pymunk.Body(body_type = pymunk.Body.KINEMATIC)
        radius = loads_coord(node['radius'])
        saw = pymunk.Circle(body, radius, pos)
        saw.filter = solid_filter
        saw.elasticity = TERRAIN_ELASTICITY 
        saw.friction = TERRAIN_FRICTION
        saw.color = (150,150,150)
        if not submode == SUBMODE_SHIELD:
            saw.collision_type = collision_types['water']
            sensor = True
        space.add(saw)
        body.reset_position = body.position
        bodies[id_]=body

    if type_ == "StartPositionNode":
        init = loads_coord(node['position'])
        startx, starty = plus(init, screen_center)
    if type_ == "FlagPositionNode":
        init = loads_coord(node['position'])
        stopx, stopy = plus(init, screen_center)

    for snap in node.get('snapped-nodes',[]):
        stype = snap['type']
        if stype=='StartPositionNode':
            pos = loads_coord(snap['position'])
            init = loads_coord(node['position'])
            offset = loads_coord(node['terrain-offset'])
            startx, starty = plus(plus(plus(init, screen_center), scale((width,height), neg(offset))), pos)
        elif stype=='FlagPositionNode':
            pos = loads_coord(snap['position'])
            init = loads_coord(node['position'])
            offset = loads_coord(node['terrain-offset'])
            stopx, stopy = plus(plus(plus(init, screen_center), scale((width,height), neg(offset))), pos)

        elif stype=='PortalNode':
            rpos = loads_coord(snap['relative-position'])
            a = loads_coord(snap['angle'])
            radius = loads_coord(snap['radius'])

            portal_id = snap['id']
            link = snap['linked-portal-id']

            dx = -radius * math.sin(a) * 10
            dy = radius * math.cos(a) * 10
            #x, y = plus(plus(plus(init, screen_center), scale((width,height), neg(offset))), pos)
            x, y = rpos

            segment = pymunk.Segment(bodies[id_], (x+dx, y+dy), (x-dx, y-dy), SEGMENT_THICKNESS)
            segment.elasticity = 999
            segment.friction = 999
            segment.color=(200,100,40)
            segment.collision_type = collision_types['portal']
            segment.pos = pos
            segment.portal_id = portal_id
            segment.portal_angle = a
            segment.linked_portal = link
            space.add(segment)

            portals[portal_id] = segment

        elif stype=='LaserNode':
            rpos = loads_coord(snap['relative-position'])
            a = loads_coord(snap['angle'])
            on = float(loads_coord(snap['phaseOnDuration']))
            off = float(loads_coord(snap['phaseOffDuration']))

            radius = 200 # FIXME until it hits a wall?
            # TODO: we will check collisions for the sensor and adjust the length of the laser accordingly
            rsens  = 80 

            x, y = rpos
            dx = radius * math.cos(a) 
            dy = radius * math.sin(a) 
            dxs = rsens * math.cos(a) 
            dys = rsens * math.sin(a) 

            #SENSOR
            segment = pymunk.Segment(bodies[id_], (x, y), (x+dxs, y+dys), SEGMENT_THICKNESS)
            segment.elasticity = 999
            segment.friction = 999
            segment.color=(80,40,0)
            segment.collision_type = collision_types['lasersensor']
            segment.period = (on+off)
            segment.onperiod = on
            segment.sensor=True
            space.add(segment)

            #LASER
            segment2 = pymunk.Segment(bodies[id_], (x, y), (x+dx, y+dy), SEGMENT_THICKNESS)
            segment2.elasticity = 999
            segment2.friction = 999
            segment2.color=(200,40,40)
            segment2.collision_type = collision_types['laser']
            segment2.period = (on+off)
            segment2.onperiod = on
            space.add(segment2)

            lasers[id_]=(segment, segment2)

        elif stype == 'MagnetNode':
            p2 = pos # no shift?
            body = pymunk.Body(body_type = pymunk.Body.KINEMATIC)
            radius = loads_coord(snap['radius'])
            strength = loads_coord(snap['strength'])
            magnet = pymunk.Circle(body, radius, p2)
            magnet.filter = pass_filter
            magnet.sensor = True
            magnet.color = (200, 200, 200)
            magnet.collision_type = collision_types['magnet']
            magnets.append((p2, radius, strength))
            space.add(magnet)

ball = pymunk.Body(mass=BALL_MASS, moment=BALL_MOMENT)

circle = pymunk.Circle(ball, radius=BALL_RADIUS)
circle.filter = solid_filter
circle.elasticity = BALL_ELASTICITY
circle.friction = BALL_FRICTION
circle.collision_type = collision_types['ball']

space.add(ball) 
space.add(circle) 

# SENSOR collision actions

dead = False
stuck = False
magnet_active = False
teleporting = None
accx = 0
accy = 0
splashed = False
tunneled = 0
tunnelxy = Vec2d(0,0)

#ANTIGRAV_FACTOR = 0.02
ANTIGRAV_FACTOR = 0.033

def hover(arbiter, space, data):
    global accx, accy
    poly = arbiter.shapes[0]
    v = poly.antigrav_strength * ANTIGRAV_FACTOR 
    a = poly.antigrav_rotation
    vx = v * math.sin(a)
    vy = v * math.cos(a)
    accx, accy = vx, vy
    return True
def unhover(arbiter, space, data):
    global accx, accy
    accx, accy = 0,0
    return True

def check_water(arbiter, space, data):
    global splashed, submode
    if splashed or not submode == SUBMODE_SHIELD:
        splashed = False
        return die(arbiter, space, data)
    splashed = True
    return True

def die(arbiter, space, data):
    global dead
    ball.velocity = (0,0)
    dead = True
    return False

def stick(arbiter, space, data):
    global stuck
    ball.velocity = (0,0)
    stuck = True
    return True

def magon(arbiter, space, data):
    global magnet_active
    magnet_active = True
    return True
def magoff(arbiter, space, data):
    global magnet_active
    magnet_active = False
    return True

def teleport(arbiter, space, data):
    #disable until this is fixed
    #return die(arbiter, space, data)

    global teleporting
    if teleporting:
        return False

    segment = arbiter.shapes[0]
    id_ = segment.portal_id
    link = segment.linked_portal
    targ = portals[link]
    if mode != MODE_HEADLESS:
        print("TELEPORT TO ",(targ.a+targ.b)/2)

    n1 = segment.normal
    n2 = targ.normal
    #th = n1.get_angle_between(n2)
    #th = (segment.b-segment.a).get_angle_between(targ.b-targ.a)
    # FIXME what about moving portals?
    # FIXME balls can end up in the wall and crash the engine
    th = segment.portal_angle - targ.portal_angle + math.pi
    if mode != MODE_HEADLESS:
        print("ROTATE BY" , numpy.rad2deg(th))
        print("VELOCITY BEFORE" , ball.velocity)
    ball.velocity = ball.velocity.rotated(-th)
    if mode != MODE_HEADLESS:
        print("VELOCITY AFTER" , ball.velocity)

    # rotation - normalize origin portal orientation and identify relative position
    if mode != MODE_HEADLESS:
        print("POSITION" , ball.position)
        print("POSITION A" , segment.a + segment.body.position)
        print("POSITION B" , segment.b + segment.body.position)
    center1 = (segment.a + segment.b) / 2.0 + segment.body.position
    relative = ball.position - center1
    if mode != MODE_HEADLESS:
        print("OFFSET BEFORE ROTATION" , relative)
    relative = relative.rotated(-th)
    if mode != MODE_HEADLESS:
        print("OFFSET AFTER ROTATION" , relative)
    center2 = (targ.a + targ.b) / 2.0 + targ.body.position
    if mode != MODE_HEADLESS:
        print("POSITION BEFORE ROTATION" , ball.position)
    ball.position = center2 + relative
    if mode != MODE_HEADLESS:
        print("POSITION AFTER ROTATION" , ball.position)

    # normalize target portal orientation and move 3 ball width away from the portal
    teleporting = True
    if mode != MODE_HEADLESS:
        print("POSITION BEFORE TRANSLATION" , ball.position)
    ball.position = ball.position - n2 * BALL_RADIUS * 3 
    if mode != MODE_HEADLESS:
        print("POSITION AFTER TRANSLATION" , ball.position)
    space.step(0.0001)
    return True

def unteleport(arbiter, space, data):
    global teleporting
    teleporting = False
    return False

def check_wall_type(arbiter, space, data):
    global tunneled, tunnelxy
    global teleporting

    teleporting = False

    point = arbiter.contact_point_set.points[0].point_a
    body = arbiter.shapes[0].body
    id_ = body.id_
    acid = acids.get(id_)
    
    # account for moving stickys and acid
    bodyxy = body.position - body.reset_position
    # TODO: account for rotating sticky and acid

    if acid and not submode == SUBMODE_SHIELD:
        imgxy = (int(round(point[0]-acid['pos'][0]-bodyxy[0])), 
                 int(round(window[1]-point[1]-acid['pos'][1]+bodyxy[1])))
        try:
            #TODO: pixel index out of range - we'll have to properly reverse calculate for rotations
            c = acid['img'].get_at(imgxy)
            if c[1] == 80:
                return die(arbiter, space, data)
        except:
            pass #ignore moving sticky/acid
    sticky = stickies.get(id_)
    if sticky and (not args.ignore_sticky) and (abs(ball.position.x - startx)>GHOST_DISTANCE or abs(ball.position.y - starty)>GHOST_DISTANCE):
        imgxy = (int(round(point[0]-sticky['pos'][0]-bodyxy[0])), 
                 int(round(window[1]-point[1]-sticky['pos'][1]+bodyxy[1])))
        try:
            #TODO: pixel index out of range - we'll have to properly reverse calculate for rotations
            c = sticky['img'].get_at(imgxy)
            if c[1] == 40:
                return stick(arbiter, space, data)
        except:
            pass #ignore moving sticky/acid
    if submode == SUBMODE_STICKY and (abs(ball.position.x - startx)>GHOST_DISTANCE or abs(ball.position.y - starty)>GHOST_DISTANCE):
       return stick(arbiter, space, data)
    if submode == SUBMODE_TUNNEL and (ball.velocity.y<0 or abs(ball.position.x - startx)>GHOST_DISTANCE or abs(ball.position.y - starty)>GHOST_DISTANCE) and ball.position.x>GHOST_DISTANCE and ball.position.x < right-GHOST_DISTANCE:
        if not tunneled:
            #print ("Tunnel start")
            #input()
            tunneled = 1
            tunnelxy = Vec2d(ball.position)
            return False
        elif tunneled == 1:
            if abs(ball.position.x - tunnelxy.x)>GHOST_DISTANCE or abs(ball.position.y - tunnelxy.y)>GHOST_DISTANCE:
                #print ("Tunnel stop", abs(ball.position.x - tunnelxy.x), abs(ball.position.y - tunnelxy.y))
                #input()
                tunneled = 2
            else:
                #print ("Not fully entered", abs(ball.position.x - tunnelxy.x), abs(ball.position.y - tunnelxy.y))
                #input()
                pass
            tunnelxy = Vec2d(ball.position)
            return False
        elif tunneled == 2:
            if abs(ball.position.x - tunnelxy.x)<GHOST_DISTANCE or abs(ball.position.y - tunnelxy.y)<GHOST_DISTANCE:
                #print ("Not fully exited", abs(ball.position.x - tunnelxy.x), abs(ball.position.y - tunnelxy.y))
                #input()
                tunnelxy = Vec2d(ball.position)
                return False
            else: 
                tunneled = 3
        # else see below
    return True

def check_laser(arbiter, space, data):
    if submode == SUBMODE_SHIELD:
        return False

    laser = arbiter.shapes[0]
    period = laser.period
    on = laser.onperiod
    if period == 0 or (now % period) <= on:
        return die(arbiter, space, data)
    else:
        return False

splash = space.add_collision_handler(
            collision_types['water'],
            collision_types['ball']
            )
splash.begin = check_water

thunk = space.add_collision_handler(
            collision_types['sand'],
            collision_types['ball']
            )
thunk.post_solve = stick

whoosh = space.add_collision_handler(
            collision_types['antigrav'],
            collision_types['ball']
            )
whoosh.begin = hover
whoosh.separate = unhover

buzz = space.add_collision_handler(
            collision_types['magnet'],
            collision_types['ball']
            )
buzz.begin = magon
buzz.separate = magoff

beam = space.add_collision_handler(
            collision_types['portal'],
            collision_types['ball']
            )
beam.pre_solve = teleport
#beam.separate = unteleport

bounce = space.add_collision_handler(
            collision_types['wall'],
            collision_types['ball']
            )
bounce.pre_solve = check_wall_type

fry = space.add_collision_handler(
            collision_types['laser'],
            collision_types['ball']
            )
fry.pre_solve = check_laser


# visual
SCALE = args.zoom

pygame.init()
screen = pygame.Surface((int(WIDTH), int(HEIGHT)))
output = pygame.display.set_mode((int(WIDTH*SCALE), int(HEIGHT*SCALE)))

if not mode == MODE_HEADLESS:
    draw_options = pymunk.pygame_util.DrawOptions(screen)

# masks - we need these in headless mode
for m in masks:
    id_ = m['id']
    img = pygame.image.load('tmp/'+id_+'.png').convert_alpha()
    if m['type']=='acid':
        img.fill((0,80,0,50), special_flags=pygame.BLEND_MIN) 
    if m['type']=='sticky':
        img.fill((80,40,40,50), special_flags=pygame.BLEND_MIN) 
    img = pygame.transform.scale(img, (m['width'], m['height']))
    m['img'] = img

STEP = 0.05
if power > 50:
    STEP = 0.025
#if mode==MODE_HEADLESS:
#    STEP = 0.0125
TIME_STEP = STEP * TIME_FACTOR

# run sim
if mode == MODE_HEADLESS:
    print("Calculating distances")

results = {}
best = None
bestdistance = None
simulating = True

tests = 0
repeat = 0
repeat_dead = 0

if mode==MODE_SPREAD:
  SPREAD_STEPS = int(spread/0.1)
  print("Spread displayed in {} steps of {}.".format(SPREAD_STEPS, (spread/SPREAD_STEPS)))

font = pygame.font.Font('freesansbold.ttf', 64)
text1 = font.render("{}".format(args.level[0]), True, (255, 255, 255), (0,0,0))
t2 = "{}".format(args.angle)
if mode==MODE_SPREAD:
    t2 += "±{}".format(spread/2.0)
t2 += " degrees"
text2 = font.render(t2, True, (255, 255, 255), (0,0,0))
text3 = font.render("{:.1f}NN {}".format(power, args.powerup), True, (255, 255, 255), (0,0,0))

while simulating:
    now = 0
    dist = None
    POWER = power * POWER_FACTOR + POWER_BASELINE
    ANGLE = angle
    splashed = False
    tunneled = False
    tunnelxy = Vec2d(0,0)

    if mode == MODE_SPREAD:
        if repeat==SPREAD_STEPS:
            ANGLE = init_angle
        else:
            ANGLE = angle - (spread/2.0)
        print ("Spread step {}, angle {}.".format(repeat, ANGLE))

    if mode == MODE_HEADLESS:
        if (ANGLE*10 % 50) == 0:
            print ("Simulating", (ANGLE, POWER))

    ball.position = (startx, starty+5)
    ball.velocity = (0,0)
    ball.angular_velocity = 0
    vy = POWER * math.sin(numpy.deg2rad(ANGLE))
    vx = POWER * math.cos(numpy.deg2rad(ANGLE))

    running = True
    cycle = 0
    stationary = 0
    dead = False
    stuck = False

    if (not mode == MODE_HEADLESS) and (repeat==0):
        for m in masks:
            screen.blit(m['img'], m['pos'], special_flags=pygame.BLEND_MAX)

        bg = screen.copy()

    for id_ in bodies.keys():
        body = bodies.get(id_)
        try:
            body.angle = getattr(body,'reset_angle')
        except:
            body.angle = 0
        try:
            body.position = getattr(body,'reset_position')
        except:
            pass #TODO?

    space.step(0.00001)

    timeout = WAIT
    while running:
        if timeout is not False and now>timeout:
            vy = POWER * math.sin(numpy.deg2rad(ANGLE))
            vx = POWER * math.cos(numpy.deg2rad(ANGLE))
            ball.position = (startx, starty+5)
            ball.velocity = (vx, vy)
            timeout = False
        elif timeout is not False:
            ball.position = (startx, starty+5)

        if not mode == MODE_HEADLESS:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            screen.blit(text1, (50, 300))
            screen.blit(text2, (50, 360))
            screen.blit(text3, (50, 420))
        if mode == MODE_SPREAD:
            xy = (int(ball.position.x), int(window[1]-ball.position.y))
            red = (255,80,80)
            green = (80,255,80)
            if repeat==SPREAD_STEPS:
                red = green
            pygame.draw.circle(bg, red, xy, int(BALL_RADIUS/2))
            #bg.set_at(xy, red)

        if cycle % 5 == 0:
            if mode == MODE_SIM or mode == MODE_SPREAD:
                screen.blit(bg,(0,0))
            if not mode == MODE_HEADLESS:
                space.debug_draw(draw_options)
                pygame.transform.scale(screen, (int(WIDTH*SCALE), int(HEIGHT*SCALE)), output)
                pygame.display.update()

        #KINEMATICS
        for id_ in rotations.keys():
            body = bodies.get(id_)
            if body:
                r = rotations[id_]
                duration = r['duration']
                then = now % duration
                t = 0 
                for s in r['steps']:
                    t = t + s['period']
                    if t>=then:
                        if s['type']=='rotate':
                            step = numpy.deg2rad(s['rotation-rate']) / s['period'] * TIME_STEP  # FIXME all movement depends on ball speed, so it is a bit moot. 
                            body.angle = body.angle - step
                            # TODO FIXME: I was told kinematic bodies can be moved by setting their velocity
                            # Needs fixing for bumper land
                            body.angular_velocity = -step
                        break
        for id_ in translations.keys():
            body = bodies.get(id_)
            if body:
                r = translations[id_]
                duration = r['duration']
                then = now % duration
                t = 0 
                #body.velocity = (0,0)
                for s in r['steps']:
                    t = t + s['period']
                    if t>=then:
                        if s['type']=='position':
                            step = TIME_STEP / s['period']
                            move = s['move-position']
                            body.position = (body.position.x + move[0] * step, body.position.y + move[1] * step)
                            #TODO FIXME: I was told kinematic bodies can be moved by setting their velocity
                            #body.velocity = Vec2d(move[0] * step, move[1] * step)
                            #def velo(body, gravity, damping, dt):
                            #    body.update_velocity(body, Vec2d(move[0] * step, move[1] * step), damping, dt)
                            #body.velocity_func = velo
                        break

        space.step(STEP)
        now += TIME_STEP
        cycle += 1

        if not timeout and abs(ball.velocity.x) < 0.001 and abs(ball.velocity.y) < 0.001:
            stationary += 1
        else:
            stationary = 0

        if dead or stuck or stationary > 100 or ball.position.y < 0 or ball.position.y > top or cycle > 2000:
            dist = tdist = 1e8 #sys.float_info.max-1 fails for sliding window calculation
            if stationary > 100 or stuck:
                # TODO: improve "proximity" function for the hole, sometimes the shot that is closest to the hole is not the smartest choice.
                dist = 0
                tdist = distance(ball.position.x, stopx, ball.position.y, stopy) # distance
                if target == 'distance':
                  dist = tdist
                elif target == 'right':
                  dist = (stopx-ball.position.x)*3 - ball.position.y # as right as possible, then low
                elif target == 'left':
                  dist = -(stopx-ball.position.x)*3 + ball.position.y # as left as possible, then low
                elif target == 'high' or target =='topright' or target =='upperleft' or target=='top':
                  dist = -ball.position.x-ball.position.y # as high as possible, then right
                elif target == 'topleft' or target =='upperleft':
                  dist = ball.position.x-ball.position.y # as high as possible, then left
                elif target == 'low' or target == 'lowerright' or target=='bottomright':
                  dist = -ball.position.x+ball.position.y*4 # as low as possible, then right
                elif target == 'lowerleft' or target=='bottomleft':
                  dist = ball.position.x+ball.position.y*4 # as low as possible, then right
                elif target == 'speed':
                  dist = 0
                if not target == "swish":
                  dist = dist + cycle  # include speed in the result
            elif mode==MODE_SPREAD:
                repeat_dead += 1
                print ("DEAD COUNTER ", repeat_dead)

            dist = dist * dist

            if tdist < 8.2:
                print ("SWISH: ", int(ANGLE*10)/10.0, " - Distance ", dist)

            running = False
            if mode == MODE_SHOW:
                simulating = False
            if mode == MODE_SPREAD:
                bg = screen.copy()
                repeat += 1
                if repeat == SPREAD_STEPS+1:
                    simulating = False

            if not dead and ((bestdistance is None) or (dist < bestdistance)):
                reason = "No reason"
                if dead:
                    reason = "Dead"
                    dist = 1e16
                elif stuck:
                    reason = "Stuck"
                elif stationary > 100:
                    reason = "Stationary"
                elif ball.position.y < 0:
                    reason = "Exit bottom"
                    dist = 1e16
                elif ball.position.y > top:
                    reason = "Exit top"
                    dist = 1e16
                elif cycle > 10000:
                    reason = "Timeout"
                if dist<1e10:
                  print("Better", angle, dist, bestdistance, reason)
                  bestdistance = dist
                  best = (ANGLE, power)

            results[round(ANGLE*10)] = dist

            stationary = 0

        # adjust ball speed for next cycle
        #ball.angular_velocity = 0 
        ball.angular_velocity = ball.angular_velocity / 1.1
        ball.velocity += (accx, accy)

        # calculate magnet activity
        if magnet_active:
            for pos, radius, strength in magnets:
                d = distance(pos[0], ball.position.x, pos[1], ball.position.y)
                if d < radius:
                    a = math.atan2(ball.position.y-pos[1], ball.position.x-pos[0])
                    p = strength / d / d * STEP * 10000
                    px = p * math.cos(a)
                    py = p * math.sin(a)
                    ball.velocity += (px, py)

    # try another angle
    angle = (round(angle * 10) + 1) / 10.0 

    tests += 1
    if (submode != SUBMODE_TUNNEL and tests == 1800) or (tests == 3600):
        simulating=False
        print ("BEST ANGLE: ", best)


if mode == MODE_HEADLESS:
    best35 = None
    for spread in range(35, 360):
       sum_ = 0

       init = int(init_angle * 10)
       for a in range(init, init + spread):
           sum_ += results[a]

       bestsum = sum_
       besta   = init

       for r in range(spread, 1700):
           sum_ = sum_ + results.get(int(init + r), 99999)
           sum_ = sum_ - results.get(int(init + r - spread), 99999)

           if sum_ < bestsum:
               bestsum = sum_
               besta = float(init + r - spread/2.0)/10.0
       
       if best35 is None:
         best35 = besta
           
         fd = None
         try:
           # writing results to JSON dump, only for levels in the correct format
           fd = open("results.json","r")
           besties = json.load(fd)
           fd.close()
  
           levelfile = args.level[0]
           path, course, level_id, ext = re.split('[/._]', levelfile)
           besties[course] = besties.get(course, {})
           besties[course][str(level_id)] = besties.get(course).get(str(level_id),{})

           key = str(power)
           if args.powerup != 'regular':
               key = args.powerup+","+str(power)

           besties[course][str(level_id)][key] = best35

           fd = open("results.json","w")
           json.dump(besties, fd, indent=2)
           fd.close()
         except Exception as x:
           print(x)
           fd.close()
           sys.exit(1)

       print ("Spread ", spread/10.0, " - BEST ANGLE ", besta)

if mode == MODE_SPREAD:
    success = SPREAD_STEPS - repeat_dead
    rate = float(success)/SPREAD_STEPS
    print ("Success rate: {:.2f}% - {}/{}".format(rate*100,success,SPREAD_STEPS))
if mode == MODE_SHOW or mode == MODE_SPREAD:
    while True:
        time.sleep(1.0)

pygame.quit()

# In HEADLESS mode, we finish by simulating the best shot in SHOW mode
if mode == MODE_HEADLESS and best:
    rerun = "{} -m spread -a {} -s 3.5 -n {} -u {} -z {} -v {} -d {} {}".format(sys.argv[0], best35, power, args.powerup, SCALE, args.vertical, WAIT, args.level[0])
    rerun = "{} -m show -a {} -s 3.5 -n {} -u {} -z {} -v {} -d {} {}".format(sys.argv[0], best[0], power, args.powerup, SCALE, args.vertical, WAIT, args.level[0])
    print(rerun)
    os.system(rerun)

