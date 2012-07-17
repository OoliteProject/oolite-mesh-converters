#!/usr/bin/python
# -*- coding: utf8 -*-


# EXTENSIONS  : "obj" "OBJ"                     # Accepted file extentions
# OSTYPES     : "****"                          # Accepted file types
# ROLE        : Editor                          # Role (Editor, Viewer, None)
# SERVICEMENU : Obj2DatTexNorm/Convert to .dat  # Name of Service menu item

"""
This script takes a Wavefront .obj file
and exports a .dat file containing the same trimesh.

This version generates files with per-vertex normals, for Oolite 1.74 and later
only.
"""


import sys
import os
import string
import argparse
import math
import decimal


args = None


#
# Vector maths libary
# These functions work on tuples of three numbers representing geometrical
# vector in 3-space.
#
def vector_add(v1, v2):
    """ vector_add
        Add two vectors.
    """
    return v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2]


def vector_subtract(v1, v2):
    """ vector_subtract
        Subtract v2 from v1.
    """
    return v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2]


def vector_scale(v, s):
    """ vector_scale
        Scale a vector by multiplying each component with a scalar.
    """
    x, y, z = v
    return x * s, y * s, z * s


def vector_flip(v):
    return vector_subtract((0, 0, 0), v)


def vector_magnitude(v):
    """ vector_magnitude
        Return the magnitude/length of a vector, denoted ‖v‖.
    """
    x, y, z = v
    return math.sqrt(x * x + y * y + z * z)


def vector_normalize(v):
    """ vector_normalize
        Return a normalized vector, i.e. one scaled so its magnitude is 1.
    """
    return vector_scale(v, 1.0 / vector_magnitude(v))


def is_vector_normalized(v):
    """ is_vector_normalized
        Test whether a vector is within 1e-5 of a normalized vector.
    """
    return abs(vector_magnitude(v) - 1.0) < 1e-5


def vector_dot_product(v1, v2):
    """ vector_dot_product
        Return the dot product (scalar product) of two vectors.
        The dot product v1 · v2 = ‖v1‖ ‖v2‖ cos θ, where θ is the angle between
        the two vectors. If both vectors are normalized, v1 · v2 = cos θ.
    """
    return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]


def vector_cross_product(v1, v2):
    """ vector_cross_product
        Returns the cross product (vector product) of two vectors.
        The cross product v1 × v2 is perpendicular to both v1 and v2 (oriented
        such that v1, v2, v1 × v2 form a clockwise wound triangle as seen from
        the origin), its magnitude is ‖v1‖ ‖v2‖ sin θ, where θ is the angle
        between v1 and v2. Note that v1 × v2 = -(v2 × v1).
    """
    x = v1[1] * v2[2] - v2[1] * v1[2]
    y = v1[2] * v2[0] - v2[2] * v1[0]
    z = v1[0] * v2[1] - v2[0] * v1[1]
    return x, y, z


def vector_normal_to_surface(v1, v2, v3):
    """ vector_normal_to_surface
        Find a normal to a surface spanned by three points.
    """
    d0 = vector_subtract(v2, v1)
    d1 = vector_subtract(v3, v2)
    return vector_normalize(vector_cross_product(d0, d1))


def average_normal(n1, n2, n3):
    """ average_normal
        Calculate the normalized sum of three vectors.
    """
    return vector_normalize(vector_add(n1, vector_add(n2, n3)))



#
# Output formatting
#
def clean_vector(v):
    """ clean_vector
        "Cleans" a vector by converting any negative zeros or values that will
        round to +/-0 to 0.
    """
    x, y, z = v
    
    def clean_number(n):
        if -0.000005 < n and n < 0.000005:
            return 0.0
        else:
            return n
    
    return clean_number(x), clean_number(y), clean_number(z)


def format_number(n):
    """ format_number
        Format a float with up to five decimal places, making it as short as
        possible without discarding information.
        
        Based on accepted answer by samplebias at
        http://stackoverflow.com/questions/5807952/removing-trailing-zeros-in-python
    """
    try:
        dec = decimal.Decimal('%.5f' % n)
    except:
        return 'bad'
    tup = dec.as_tuple()
    delta = len(tup.digits) + tup.exponent
    digits = ''.join(str(d) for d in tup.digits)
    if delta <= 0:
        zeros = abs(tup.exponent) - len(tup.digits)
        val = '0.' + ('0' * zeros) + digits
    else:
        val = digits[:delta] + ('0' * tup.exponent) + '.' + digits[delta:]
    val = val.rstrip('0')
    if val[-1] == '.':
        val = val[:-1]
    
    if tup.sign:
        return '-' + val
    else:
        return val


def format_vector(v):
    if args.pretty_output:
        return '% .5f,% .5f,% .5f' % v
    else:
        x, y, z = v
        return '%s %s %s' % (format_number(x), format_number(y), format_number(z))


def format_normal(n):
    if args.flip_normals:
        return format_vector(vector_flip(n))
    else:
        return format_vector(n)


def format_textcoord(st):
    if args.pretty_output:
        return '% .5f,% .5f' % st
    else:
        s, t = st
        return '%s %s' % (format_number(s), format_number(t))


#
# Argument handling
#
class _ListWindingModesAction(argparse.Action):
    
    """ _ListWindingModesAction
        Argparse action to handle the --list-winding-modes option. This is
        implemented as an action so we don't get the standard "error: too few
        arguments" message.
        
        Based on argparse's _HelpAction.
    """
    
    def __init__(self,
                 option_strings,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
                 help=None):
        super(_ListWindingModesAction, self).__init__(
              option_strings=option_strings,
              dest=dest,
              default=default,
              nargs=0,
              help=help)
    
    def __call__(self, parser, namespace, values, option_string=None):
        print '''Winding determines which side of a triangle is the outside.
The --winding-mode option controls how the winding is selected for each
triangle. If a model appears "inside-out" or has missing faces, you need
to adjust this.

Available modes:
  0: maintain the OBJ file's original winding.
  1: reverse the OBJ file's winding.
  2: select winding automatically for each face based on normals.
  3: select winding automatically for each face, but buggily (the same
     behaviour as Oolite for old-style model files). You probably don't
     want this.'''
        parser.exit()






argParser = argparse.ArgumentParser(description='''Convert OBJ meshes to Oolite DAT format.
                                                   This tool preserves normals (face directions for lighting purposes)
                                                   stored in the OBJ file, rather than making Oolite recalculate them.''')
argParser.add_argument('files', nargs='+',
                  help='the files to convert')
argParser.add_argument('-w', '--winding-mode', type=int, default=2, metavar='MODE', dest='winding_mode',
                  help='''Specify winding mode (default: %(default)s). Winding determines which side of a triangle is out.
                          Run %(prog)s --list-winding-modes for more information.''')
argParser.add_argument('-f', '--flip-normals', action='store_true', dest='flip_normals',
                       help='Reverse normals; this turns the lighting inside out without affecting face visibility')
argParser.add_argument('--include-face-normals', action='store_true', dest='include_face_normals',
                       help=argparse.SUPPRESS) # No help because this is only useful when targeting versions earlier than 1.74.
argParser.add_argument('-m', '--preserve-material-names', action='store_false', dest='rename_materials',
                       help='Keep abstract material names from material library, instead of renaming materials after their diffuse map. Only use if you\'ll be creating material dictionaries.')
argParser.add_argument('-p', '--pretty-output', action='store_true', dest='pretty_output',
                       help='Create a file that\'s easier for humans to read, but larger and slower to parse')

argParser.add_argument('-L', '--list-winding-modes', action=_ListWindingModesAction,
                       help=argparse.SUPPRESS)

args = argParser.parse_args()


#
# Processing helpers
#
def vertex_reference(n, nv):
    if n < 0:
        return n + nv
    else:
        return n - 1


resolved_vertex_count = 0
def resolve_vertex(v, vn, index_for_vert_and_norm, vertex_lines_out, normals_lines_out):
    """ resolve_vertex
        Returns a unique index for each (vertex, normal) pair. When a new pair
        is seen, a new index is generated and the relevant lines are added to
        the output buffers for the VERTEX and NORMALS sections.
        
        This is necessary because OBJ uses separate index spaces for vertex
        positions and normals, but DAT requires one index per pair.
    """
    global resolved_vertex_count
    v = clean_vector(v)
    vn = clean_vector(vn)
    key = v, vn
    if key in index_for_vert_and_norm:
        return index_for_vert_and_norm[key]
    else:
        result = resolved_vertex_count
        resolved_vertex_count = resolved_vertex_count + 1
        
        index_for_vert_and_norm[key] = result
        
        vertex_lines_out.append(format_vector(v) + '\n')
        if not is_vector_normalized(vn):
            print 'Bug: writing unnormalized normal %s' % format_normal(vn)
        normals_lines_out.append(format_normal(vn) + '\n')
        
        return result


def should_reverse_winding(v1, v2, v3, normal):
    """ should_reverse_winding
        Determine whether to reverse the winding of the triangle (v1, v2, v3)
        based on current winding mode and face normal.
    """
    if args.winding_mode == 0:
        return False
    
    elif args.winding_mode == 1:
        return True
    
    else:
        calculatedNormal = vector_normal_to_surface(v3, v2, v1)
        if normal == (0, 0, 0):
            normal = vector_flip(calculatedNormal)
        
        if args.winding_mode == 2:
            # Guess, using the assumptions that normals should point more "outwards"
            # than "inwards".
            if (vector_dot_product(normal, calculatedNormal) < 0.0):
                return True
            else:
                return False
        
        elif args.winding_mode == 3:
            # Buggy calculation traditionally used by Oolite.
            if (normal[0] * calculatedNormal[0] < 0.0) or (normal[1] * calculatedNormal[1] < 0.0) or (normal[2] * calculatedNormal[2] < 0.0):
                return True
            else:
                return False
    
    print 'Unknown normal winding mode %u' % (args.winding_mode)
    exit(-1)


#
# Grand processing loop
#
for input_file_name in args.files:
    # Select output name and open files
    output_file_name = input_file_name.lower().replace('.obj', '.dat')
    if output_file_name == input_file_name:
        output_file_name += '.1'
    input_display_name = os.path.basename(input_file_name)
    output_display_name = os.path.basename(output_file_name)
    
    print input_display_name + ' -> ' + output_display_name
    
    input_file = open(input_file_name, 'r')
    lines = input_file.read().splitlines(0)
    output_file = open(output_file_name, 'w')
    
    ### Set up state used in parsing and generating output
    vertex_lines_out = ['VERTEX\n']
    faces_lines_out = ['FACES\n']
    normals_lines_out = ['NORMALS\n']
    vertex_count = 0
    face_count = 0
    normal_count = 0
    skips = 0
    vertex=[]
    uv=[]
    normal=[]
    face=[]
    texture=[]
    texture_for_face=[]
    texcoords_for_face=[]
    interpret_texture = 0
    material_rename = {}
    index_for_vert_and_norm = {}
    names_lines_out = []
    materials_used = []
    max_v = [0.0, 0.0, 0.0]
    min_v = [0.0, 0.0, 0.0]
    
    ### Find materials from material library
    for line in lines:
        tokens = string.split(line)
        if tokens != []:
            if tokens[0] == 'mtllib':
                path = os.path.dirname(input_file_name)
                material_file_name = os.path.join(path, tokens[1])
                print '  Material library file: %s' % material_file_name
                material_file = open(material_file_name, 'r')
                new_material = False
                for material_line in material_file.read().splitlines(0):
                    material_tokens = string.split(material_line)
                    if material_tokens != []:
                        if material_tokens[0] == 'newmtl':
                            new_material_name = material_tokens[1]
                            if args.rename_materials:
                                # Let map_Kd handler deal with material table.
                                # FIXME: produce cleaner results if there is no diffuse map.
                                new_material = True
                            else:
                                # Store material key in used material list and (if using short names) the rename table.
                                materials_used.append(new_material_name)
                                if not args.pretty_output:
                                    material_rename[new_material_name] = len(material_rename)
                                    names_lines_out.append(new_material_name + '\n')
                        
                        if material_tokens[0] == 'map_Kd':
                            # If this is the first diffuse map for this material...
                            if new_material:
                                # Add it to the used materials list and rename table.
                                name = material_tokens[1]
                                materials_used.append(name)
                                print '  Material %s -> %s' % (new_material_name, name)
                                if args.pretty_output:
                                    material_rename[new_material_name] = name
                                else:
                                    material_rename[new_material_name] = len(material_rename)
                                    names_lines_out.append(name + '\n')
                            new_material = False
                material_file.close()
    
    ### Parse vertices
    for line in lines:
        tokens = string.split(line)
        if tokens != []:
            if tokens[0] == 'v':
                vertex_count = vertex_count + 1
                # Negate x value for vertex to compensate for different coordinate conventions.
                x = -float(tokens[1])
                y = float(tokens[2])
                z = float(tokens[3])
                vertex.append((x, y, z))
                if x > max_v[0]: max_v[0] = x
                if y > max_v[1]: max_v[1] = y
                if z > max_v[2]: max_v[2] = z
                if x < min_v[0]: min_v[0] = x
                if y < min_v[1]: min_v[1] = y
                if z < min_v[2]: min_v[2] = z
                    
            if tokens[0] == 'vn':
                normal_count = normal_count + 1
                x = -float(tokens[1])
                y = float(tokens[2])
                z = float(tokens[3])
                n = (x, y, z)
                if not is_vector_normalized(n):
                    print 'Warning: read unnormalized normal %s' % format_vector(n)
                normal.append(vector_normalize((x, y, z)))
                
            if tokens[0] == 'vt':
                uv.append((float(tokens[1]), 1.0 - float(tokens[2])))
    
    ### Parse faces
    group_token = 0
    for line in lines:
        tokens = string.split(line)
        if (tokens != []):
            if (tokens[0] == 'usemtl'):
                textureName = tokens[1]
                if (material_rename.has_key(textureName)):
                    textureName = material_rename[textureName]
                interpret_texture = 1
                texture.append(textureName)
            
            if (tokens[0] == 'f'):
                while (len(tokens) >=4):
                    bits = string.split(tokens[1], '/')
                    v1 = vertex_reference(int(bits[0]), vertex_count)
                    if (bits[1] > ''): vt1 = vertex_reference(int(bits[1]), vertex_count)
                    if (bits[2] > ''): vn1 = vertex_reference(int(bits[2]), normal_count)
                    
                    bits = string.split(tokens[2], '/')
                    v2 = vertex_reference(int(bits[0]), vertex_count)
                    if (bits[1] > ''): vt2 = vertex_reference(int(bits[1]), vertex_count)
                    if (bits[2] > ''): vn2 = vertex_reference(int(bits[2]), normal_count)
                    
                    bits = string.split(tokens[3], '/')
                    v3 = vertex_reference(int(bits[0]), vertex_count)
                    if (bits[1] > ''):
                        vt3 = vertex_reference(int(bits[1]), vertex_count)
                    else:
                        if interpret_texture:
                            print 'File does not provide texture coordinates! Materials will not be exported.'
                        interpret_texture = 0
                    if (bits[2] > ''): vn3 = vertex_reference(int(bits[2]), normal_count)
                    
                    d0 = (vertex[v2][0] - vertex[v1][0], vertex[v2][1] - vertex[v1][1], vertex[v2][2] - vertex[v1][2])
                    d1 = (vertex[v3][0] - vertex[v2][0], vertex[v3][1] - vertex[v2][1], vertex[v3][2] - vertex[v2][2])
                    xp = (d0[1] * d1[2] - d0[2] * d1[1], d0[2] * d1[0] - d0[0] * d1[2], d0[0] * d1[1] - d0[1] * d1[0])
                    det = math.sqrt(xp[0]*xp[0] + xp[1]*xp[1] + xp[2]*xp[2])
                    if (det > 0):
                        rv1 = resolve_vertex(vertex[v1], normal[vn1], index_for_vert_and_norm, vertex_lines_out, normals_lines_out)
                        rv2 = resolve_vertex(vertex[v2], normal[vn2], index_for_vert_and_norm, vertex_lines_out, normals_lines_out)
                        rv3 = resolve_vertex(vertex[v3], normal[vn3], index_for_vert_and_norm, vertex_lines_out, normals_lines_out)
                        face_normal = average_normal(normal[vn1], normal[vn2], normal[vn3])
                        
                        if should_reverse_winding(vertex[v1], vertex[v2], vertex[v3], face_normal):
                            # If reversing, swap first and third vertex index and tex coord.
                            # Note that we don't need to swap normals here, because they're
                            # indexed in the same sequence as vertices, but texture coords
                            # are stored separately with the faces.
                            temp = rv1
                            rv1 = rv3
                            rv3 = temp
                            temp = vt1
                            vt1 = vt3
                            vt3 = temp
                        
                        if args.include_face_normals:
                            face_normal_str = format_normal(face_normal)
                        else:
                            face_normal_str = '0 0 0'
                        
                        face_count = face_count + 1
                        face.append((rv1, rv2, rv3))
                        faces_lines_out.append('0 0 0\t%s\t3\t%d %d %d\n' % (face_normal_str, rv1, rv2, rv3))
                        
                        if interpret_texture:
                            texture_for_face.append(textureName)
                            texcoords_for_face.append([uv[vt1], uv[vt2], uv[vt3]])
                    
                    tokens = tokens[:2]+tokens[3:]
    
    ### Write output.
    output_file.write('// Converted by Obj2DatTexNorm.py Wavefront OBJ file conversion script\n')
    output_file.write('// (c) 2005-2012 By Giles Williams and Jens Ayton\n')
    output_file.write('// \n')
    output_file.write('// original file: "%s"\n' % input_display_name)
    output_file.write('// \n')
    output_file.write('// model size: %.3f x %.3f x %.3f\n' % (max_v[0]-min_v[0], max_v[1]-min_v[1], max_v[2]-min_v[2]))
    output_file.write('// \n')
    output_file.write('// materials used: %s\n' % materials_used)
    output_file.write('// \n')
    output_file.write('NVERTS %d\n' % resolved_vertex_count)
    output_file.write('NFACES %d\n' % face_count)
    output_file.write('\n')
    output_file.writelines(vertex_lines_out)
    output_file.write('\n')
    output_file.writelines(faces_lines_out)
    output_file.write('\n')
    
    # Check that we have textures for every vertex
    ok_to_write_texture = 1
    if len(texture_for_face) != len(face):
        ok_to_write_texture = 0
    if len(texcoords_for_face) != len(face):
        ok_to_write_texture = 0
    for texture in texture_for_face:
        if texture == '':
            ok_to_write_texture = 0
    
    # If we're all clear then write out the texture uv coordinates.
    if ok_to_write_texture:
        output_file.write('TEXTURES\n')
        for i in range(0, len(face)):
            facet = face[i]
            texture = texture_for_face[i]
            output_file.write('%s\t1.0 1.0\t%s\t%s\t%s\n' %
                              (texture, format_textcoord(texcoords_for_face[i][0]),
                               format_textcoord(texcoords_for_face[i][1]),
                               format_textcoord(texcoords_for_face[i][2])))
    output_file.write('\n')
    
    # Write NAMES section if used (textures in place and not pretty printing)
    if len(names_lines_out) != 0:
        output_file.write('NAMES %u\n' % len(names_lines_out))
        output_file.writelines(names_lines_out)
        output_file.write('\n')
    
    output_file.writelines(normals_lines_out)
    output_file.write('\n')
    output_file.write('END\n')
    output_file.close()
    input_file.close()


print 'Done.\n'
