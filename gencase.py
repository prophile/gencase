"""Button case generator, v0.0.1

Usage: gencase.py (case | lid | assembly) [options]

Options:
  --width=<w>       Case width, in mm [default: 100].
  --length=<l>      Case length, in mm [default: 100].
  --thickness=<th>  Shell thickness, in mm [default: 5].
  --depth=<d>       Case depth, in mm [default: 60].
  --button=<b>      Button diameter, in mm [default: 22].
  --cable=<c>       Cable diameter, in mm [default: 5].
  --clearance=<kl>  Hole clearance, in mm [default: 1].
  --surface         Add button surface with chamfer.
  --help            Show this help.
  --version         Show version information.
"""

from docopt import docopt
from collections import namedtuple
from decimal import Decimal

CASE = 'c'
LID = 'l'

Settings = namedtuple('Settings',
                      'button cable clearance thickness depth length width '
                      'with_surface parts')

class Mesh(object):
    def __init__(self):
        self.quantum = Decimal('1.00')
        self.vertices = {}
        self.vertex_array = []
        self.faces = set()

    def get_vertex(self, pos):
        posn = (self._quantize(pos[0]),
                self._quantize(pos[1]),
                self._quantize(pos[2]))
        if posn in self.vertices:
            return self.vertices[posn]
        else:
            index = len(self.vertex_array)
            self.vertex_array.append(posn)
            self.vertices[posn] = index
            return index

    def add_face(self, a, b, c, d = None):
        if d is not None:
            self.add_face(a, b, c)
            self.add_face(a, c, d)
            return
        va = self.get_vertex(a)
        vb = self.get_vertex(b)
        vc = self.get_vertex(c)
        try:
            self.faces.remove((vc, vb, va))
        except KeyError:
            self.faces.add((va, vb, vc))

    def write(self, f):
        f.write('# Auto-generated\n')
        for vtx in self.vertex_array:
            f.write('v {0} {1} {2}\n'.format(*vtx))
        f.write('\n')
        for face in self.faces:
            f.write('f {0} {1} {2}\n'.format(face[0] + 1,
                                             face[1] + 1,
                                             face[2] + 1))

    def _quantize(self, value):
        raw = Decimal(value)
        return raw.quantize(self.quantum)

def generate_chamfer(width, length, thickness, height):
    hw = width * 0.5
    hl = length * 0.5
    yield ((-hw, -hl, height),
           (-hw + thickness, -hl + thickness, height - thickness),
           (hw - thickness, -hl + thickness, height - thickness),
           (hw, -hl, height))
    yield reversed(((-hw, hl, height),
           (-hw + thickness, hl - thickness, height - thickness),
           (hw - thickness, hl - thickness, height - thickness),
           (hw, hl, height)))
    yield reversed(((-hw, -hl, height),
           (-hw + thickness, -hl + thickness, height - thickness),
           (-hw + thickness, hl - thickness, height - thickness),
           (-hw, hl, height)))
    yield ((hw, -hl, height),
           (hw - thickness, -hl + thickness, height - thickness),
           (hw - thickness, hl - thickness, height - thickness),
           (hw, hl, height))

def pairwise(iterable):
    from itertools import tee
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

def triplewise(iterable):
    from itertools import tee
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b, c = tee(iterable, 3)
    next(b, None)
    next(c, None)
    next(c, None)
    return zip(a, b, c)

def generate_corner(radius, full = False):
    from math import sin, cos, pi
    POINTS = 30
    if full:
        POINTS *= 4
        TOTAL = 2*pi
    else:
        TOTAL = (pi/2)
    for i in range(POINTS + 1):
        angle = (i/POINTS) * TOTAL
        yield ((-sin(angle) * radius,
                -cos(angle) * radius))

def generate_corner_with_hole(width, length, hole):
    hw = width * 0.5
    hl = length * 0.5
    points = [(0, -hl, 0)]
    for x, y in generate_corner(hole):
        points.append((x, y, 0))
    points.append((-hw, 0, 0))
    for a, b in pairwise(points):
        yield ((-hw, -hl, 0),
               a, b)

def generate_hole_edge(radius, depth):
    points = []
    for x, y in generate_corner(radius, True):
        points.append((x, y, 0))
        points.append((x, y, depth))
    invert = True
    for a, b, c in triplewise(points):
        if invert:
            yield c, b, a
        else:
            yield a, b, c
        invert = not invert

def generate_face_with_hole(width, length, hole):
    yield from generate_corner_with_hole(width, length, hole)
    yield from transform(generate_corner_with_hole(width, length, hole),
                         lambda x, y, z: (-x, y, z),
                         inverting = True)
    yield from transform(generate_corner_with_hole(width, length, hole),
                         lambda x, y, z: (x, -y, z),
                         inverting = True)
    yield from transform(generate_corner_with_hole(width, length, hole),
                         lambda x, y, z: (-x, -y, z),
                         inverting = False)

def generate_face(width, length, thickness = 5, hole = 0, height = 0):
    #if hole:
    #    raise NotImplementedError('no hole support yet')
    # Generate chamfer
    hw = width * 0.5
    hl = length * 0.5
    yield from generate_chamfer(width, length, thickness, height)
    if hole:
        yield from transform(generate_face_with_hole(width, length, hole),
                             t = lambda x, y, z: (x, y, z + height))
        yield from transform(generate_face_with_hole(width - thickness*2,
                                                     length - thickness*2,
                                                     hole),
                             t = lambda x, y, z: (x, y, height + z - thickness),
                             inverting = True)
        yield from transform(generate_hole_edge(hole, thickness),
                             t = lambda x, y, z: (x, y, height + z - thickness))
    else:
        yield ((-hw, -hl, height),
               ( hw, -hl, height),
               ( hw,  hl, height),
               (-hw,  hl, height))
        yield ((-hw + thickness, -hl + thickness, height - thickness),
               (-hw + thickness,  hl - thickness, height - thickness),
               ( hw - thickness,  hl - thickness, height - thickness),
               ( hw - thickness, -hl + thickness, height - thickness))

def transform(source, t = lambda x, y, z: (x, y, z), inverting = False):
    for item in source:
        result = (t(*x) for x in item)
        if inverting:
            yield tuple(reversed(tuple(result)))
        else:
            yield tuple(result)

def emit_solid_case(settings):
    m = Mesh()
    hw = settings.width * 0.5
    hl = settings.length * 0.5
    d = settings.depth
    hd = d * 0.5
    def produce(*args, **kwargs):
        for face in transform(*args, **kwargs):
            m.add_face(*tuple(face))
    if LID in settings.parts:
        # Top face
        produce(generate_face(settings.width, settings.length,
                              settings.thickness, height = d,
                              hole = settings.button + settings.clearance))
        if settings.with_surface:
            produce(generate_face(settings.width, settings.length,
                                  settings.thickness,
                                  hole = settings.button + settings.clearance),
                    lambda x, y, z: (x, y, -z + d),
                    inverting = True)
    if CASE in settings.parts:
        # Bottom face
        produce(generate_face(settings.width, settings.length,
                              settings.thickness),
                lambda x, y, z: (x, y, -z),
                inverting = True)
        # Side faces
        produce(generate_face(settings.width, settings.depth,
                              settings.thickness),
                lambda x, y, z: (x, -z - hl, hd + y),
                inverting = False)
        produce(generate_face(settings.width, settings.depth,
                              settings.thickness,
                              hole = settings.cable + settings.clearance),
                lambda x, y, z: (x, z + hl, hd + y),
                inverting = True)
        produce(generate_face(settings.length, settings.depth,
                              settings.thickness),
                lambda x, y, z: (z + hw, x, hd + y),
                inverting = False)
        produce(generate_face(settings.length, settings.depth,
                              settings.thickness),
                lambda x, y, z: (-z - hw, x, hd + y),
                inverting = True)
    import sys
    m.write(sys.stdout)

def parse_args(args):
    return docopt(__doc__, version = __doc__.splitlines()[0])

def to_settings(parsed_args):
    if parsed_args['lid']:
        parts = LID
    elif parsed_args['case']:
        parts = CASE
    elif parsed_args['assembly']:
        parts = LID + CASE
    return Settings(button = float(parsed_args['--button']),
                    cable = float(parsed_args['--cable']),
                    clearance = float(parsed_args['--clearance']),
                    thickness = float(parsed_args['--thickness']),
                    depth = float(parsed_args['--depth']),
                    width = float(parsed_args['--width']),
                    length = float(parsed_args['--length']),
                    with_surface = parsed_args['--surface'],
                    parts = parts)

def main(args):
    parsed_args = parse_args(args)
    settings = to_settings(parsed_args)
    emit_solid_case(settings)

if __name__ == '__main__':
    import sys
    main(sys.argv)

