#!/usr/bin/python

# EXTENSIONS  : "obj" "OBJ"						# Accepted file extentions
# OSTYPES     : "****"							# Accepted file types
# ROLE        : Editor							# Role (Editor, Viewer, None)
# SERVICEMENU : Obj2DatTexNorm/Convert to .dat	# Name of Service menu item

"""
This script takes a Wavefront .obj file
and exports a .dat file containing the same trimesh.

This version generates files with per-vertex normals, for Oolite 1.74 and later
only.
"""


args = None


import sys, os, string, argparse, math, decimal

def vertex_reference(n, nv):
	if n < 0:
		return n + nv
	return n - 1


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
	"""	format_number
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
		val = '0.' + ('0'*zeros) + digits
	else:
		val = digits[:delta] + ('0'*tup.exponent) + '.' + digits[delta:]
	val = val.rstrip('0')
	if val[-1] == '.':
		val = val[:-1]
	if tup.sign:
		return '-' + val
	return val


def format_vertex(v):
	if args.pretty_output:
		return '% .5f,% .5f,% .5f' % v
	else:
		x, y, z = v
		return '%s %s %s' % (format_number(x), format_number(y), format_number(z))


def format_normal(n):
	if args.flip_normals:
		return format_vertex(vector_flip(n))
	else:
		return format_vertex(n)


def format_textcoord(st):
	if args.pretty_output:
		return '% .5f,% .5f' % st
	else:
		s, t = st
		return '%s %s' % (format_number(s), format_number(t))


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
		
		vertex_lines_out.append(format_vertex(v) + '\n')
		normals_lines_out.append(format_normal(vn) + '\n')
		
		return result


def normalize(n):
	""" normalize
		Normalize a vector, specified as a tuple of three components.
	"""
	x, y, z = n
	scale = 1.0 / math.sqrt(x * x + y * y + z * z)
	return x * scale, y * scale, z * scale


def vector_add(v1, v2):
	return v1[0] + v2[0], v1[1] + v2[1], v1[2] + v2[2]


def vector_subtract(v1, v2):
	return v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2]


def vector_flip(v):
	return vector_subtract((0, 0, 0), v)


def dot_product(v1, v2):
	return v1[0] * v2[0] + v1[1] * v2[1] + v1[1] * v2[1]


def cross_product(v1, v2):
	x = v1[1] * v2[2] - v2[1] * v1[2]
	y = v1[2] * v2[0] - v2[2] * v1[0]
	z = v1[0] * v2[1] - v2[0] * v1[1]
	return x, y, z


def average_normal(n1, n2, n3):
	""" average_normal
		Calculate the normalized sum of three vectors.
	"""
	return normalize(vector_add(n1, vector_add(n2, n3)))


def normal_to_surface(v1, v2, v3):
	""" normal_to_surface
		Find a normal to a surface spanned by three points.
	"""
	d0 = vector_subtract(v2, v1)
	d1 = vector_subtract(v3, v2)
	return normalize(cross_product(d0, d1))


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
		calculatedNormal = normal_to_surface(v3, v2, v1)
		if normal == (0, 0, 0):
			normal = vector_flip(calculatedNormal)
		
		if args.winding_mode == 2:
			# Guess, using the assumptions that normals should point more "outwards"
			# than "inwards".
			if (dot_product(normal, calculatedNormal) < 0.0):
				return True
			else:
				return False
		
		elif args.winding_mode == 3:
			# Buggy calculation traditionally used by Oolite.
			if (normal[0] * calculatedNormal[0] < 0.0) or (normal[1] * calculatedNormal[1] < 0.0) or (normal[2] * calculatedNormal[2] < 0.0):
				return True
			else:
				return False
	
	print 'Unknown normal winding mode %u' % ( args.winding_mode )
	exit(-1)


class ListWindingModesAction(argparse.Action):
	
	""" ListWindingModesAction
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
		super(ListWindingModesAction, self).__init__(
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
argParser.add_argument('-p', '--pretty-output', action='store_true', dest='pretty_output',
					   help='Create a file that\'s easier for humans to read, but larger and slower to parse')

argParser.add_argument('-l', '--list-winding-modes', action=ListWindingModesAction,
					   help='Show the available winding modes and exit')

args = argParser.parse_args()


for inputFileName in args.files:
	# Select output name and open files
	outputFileName = inputFileName.lower().replace('.obj', '.dat')
	if outputFileName == inputFileName:
		outputFileName = outputFileName,append('.1')
	inputDisplayName = os.path.basename(inputFileName)
	outputDisplayName = os.path.basename(outputFileName)
	
	print inputDisplayName + ' -> ' + outputDisplayName
	
	inputFile = open(inputFileName, 'r')
	lines = inputFile.read().splitlines(0)
	outputFile = open(outputFileName, 'w')
	
	### Set up state used in parsing and generating output
	vertex_lines_out = ['VERTEX\n']
	faces_lines_out = ['FACES\n']
	normals_lines_out = ['NORMALS\n']
	n_verts = 0
	n_faces = 0
	n_normals = 0
	skips = 0
	vertex=[]
	uv=[]
	normal=[]
	face=[]
	texture=[]
	uvForVertex=[]
	uvsForTexture={}
	textureForFace=[]
	uvsForFace=[]
	textureCounter = 0
	interpretTexture = 0
	materials = {}
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
				path = os.path.dirname(inputFileName)
				materialfilename = os.path.join(path, tokens[1]);
				print '  Material library file: %s' % materialfilename
				infile = open( materialfilename, 'r')
				mlines = infile.read().splitlines(0)
				newMaterial = 0
				for mline in mlines:
					tokens1 = string.split(mline)
					if tokens1 != []:
						if tokens1[0] == 'newmtl':
							newMaterialName = tokens1[1]
							newMaterial = 1
						if tokens1[0] == 'map_Kd':
							if newMaterial:
								name = tokens1[1]
								materials_used.append(name)
								print '  Material %s -> %s' % (newMaterialName, name)
								if args.pretty_output:
									materials[newMaterialName] = name
								else:
									index = len(materials)
									materials[newMaterialName] = index
									names_lines_out.append(name + '\n')
							newMaterial = 0
	
	### Print materials
	# find geometry vertices first
	for line in lines:
		tokens = string.split(line)
		if tokens != []:
			if tokens[0] == 'v':
				n_verts = n_verts + 1
				# Negate x value for vertex to compensate for different coordinate conventions.
				x = -float(tokens[1])
				y = float(tokens[2])
				z = float(tokens[3])
				vertex.append( ( x, y, z) )
				if (x > max_v[0]):
					max_v[0] = x
				if (y > max_v[1]):
					max_v[1] = y
				if (z > max_v[2]):
					max_v[2] = z
				if (x < min_v[0]):
					min_v[0] = x
				if (y < min_v[1]):
					min_v[1] = y
				if (z < min_v[2]):
					min_v[2] = z
					
			if tokens[0] == 'vn':
				n_normals = n_normals + 1
				x = -float(tokens[1])
				y = float(tokens[2])
				z = float(tokens[3])
				normal.append(normalize((x, y, z)))
				
			if tokens[0] == 'vt':
				uv.append((float(tokens[1]), 1.0 - float(tokens[2])))
	
	### Parse geometry
	group_token = 0
	for line in lines:
		tokens = string.split(line)
		if (tokens != []):
			if (tokens[0] == 'usemtl'):
				textureName = tokens[1]
				if (materials.has_key(textureName)):
					textureName = materials[textureName]
				interpretTexture = 1
				texture.append(textureName)
				uvsForTexture[textureName] = n_verts * [[]]
			if (tokens[0] == 'f'):
				while (len(tokens) >=4):
					bits = string.split(tokens[1], '/')
					v1 = vertex_reference(int(bits[0]), n_verts)
					if (bits[1] > ''):
						vt1 = vertex_reference(int(bits[1]), n_verts)
					if (bits[2] > ''):
						vn1 = vertex_reference(int(bits[2]), n_normals)
					bits = string.split(tokens[2], '/')
					v2 = vertex_reference(int(bits[0]), n_verts)
					if (bits[1] > ''):
						vt2 = vertex_reference(int(bits[1]), n_verts)
					if (bits[2] > ''):
						vn2 = vertex_reference(int(bits[2]), n_normals)
					bits = string.split(tokens[3], '/')
					v3 = vertex_reference(int(bits[0]), n_verts)
					if (bits[1] > ''):
						vt3 = vertex_reference(int(bits[1]), n_verts)
					else:
						if interpretTexture:
							print 'File does not provide texture coordinates! Materials will not be exported.'
						interpretTexture = 0
					if (bits[2] > ''):
						vn3 = vertex_reference(int(bits[2]), n_normals)
					
					d0 = (vertex[v2][0] - vertex[v1][0], vertex[v2][1] - vertex[v1][1], vertex[v2][2] - vertex[v1][2])
					d1 = (vertex[v3][0] - vertex[v2][0], vertex[v3][1] - vertex[v2][1], vertex[v3][2] - vertex[v2][2])
					xp = (d0[1] * d1[2] - d0[2] * d1[1], d0[2] * d1[0] - d0[0] * d1[2], d0[0] * d1[1] - d0[1] * d1[0])
					det = math.sqrt(xp[0]*xp[0] + xp[1]*xp[1] + xp[2]*xp[2])
					if (det > 0):
						rv1 = resolve_vertex(vertex[v1], normal[vn1], index_for_vert_and_norm, vertex_lines_out, normals_lines_out)
						rv2 = resolve_vertex(vertex[v2], normal[vn2], index_for_vert_and_norm, vertex_lines_out, normals_lines_out)
						rv3 = resolve_vertex(vertex[v3], normal[vn3], index_for_vert_and_norm, vertex_lines_out, normals_lines_out)
						face_normal = average_normal(normal[vn1], normal[vn2], normal[vn3]);
						
						if should_reverse_winding(vertex[v1], vertex[v2], vertex[v3], face_normal):
							# If reversing, swap first and third vertex index and tex coord.
							# Note that we don't need to swap normals here, because they're indexed
							# in the same series as vertices, but texture coords are stored
							# separately with the faces.
							temp = rv1
							rv1 = rv3
							rv3 = temp
							temp = vt1
							vt1 = vt3
							vt3 = temp
						
						if not args.include_face_normals:
							face_normal_str = '0 0 0'
						else:
							face_normal_str = format_normal(face_normal)
						
						n_faces = n_faces + 1
						face.append((rv1, rv2, rv3))
						faces_lines_out.append('0 0 0\t%s\t3\t%d %d %d\n' % (face_normal_str, rv1, rv2, rv3))
						
						if (interpretTexture):
							textureForFace.append(textureName)
							uvsForTexture[textureName][v1] = uv[vt1]
							uvsForTexture[textureName][v2] = uv[vt2]
							uvsForTexture[textureName][v3] = uv[vt3]
							uvsForFace.append([ uv[vt1], uv[vt2], uv[vt3]])
					tokens = tokens[:2]+tokens[3:]
	
	### Write output.
	outputFile.write('// Converted by Obj2DatTexNorm.py Wavefront OBJ file conversion script\n')
	outputFile.write('// (c) 2005-2012 By Giles Williams and Jens Ayton\n')
	outputFile.write('// \n')
	outputFile.write('// original file: "%s"\n' % inputDisplayName)
	outputFile.write('// \n')
	outputFile.write('// model size: %.3f x %.3f x %.3f\n' % ( max_v[0]-min_v[0], max_v[1]-min_v[1], max_v[2]-min_v[2]))
	outputFile.write('// \n')
	outputFile.write('// materials used: %s\n' % materials_used)
	outputFile.write('// \n')
	outputFile.write('NVERTS %d\n' % resolved_vertex_count)
	outputFile.write('NFACES %d\n' % n_faces)
	outputFile.write('\n')
	outputFile.writelines(vertex_lines_out)
	outputFile.write('\n')
	outputFile.writelines(faces_lines_out)
	outputFile.write('\n')
	
	# Check that we have textures for every vertex
	okayToWriteTexture = 1
	if (len(textureForFace) != len(face)):
		okayToWriteTexture = 0
	if (len(uvsForFace) != len(face)):
		okayToWriteTexture = 0
	for texture in textureForFace:
		if (texture == ''):
			okayToWriteTexture = 0
	
	# If we're all clear then write out the texture uv coordinates.
	if (okayToWriteTexture):
		outputFile.write('TEXTURES\n')
		for i in range(0, len(face)):
			facet = face[i]
			texture = textureForFace[i]
			uvForVertex = uvsForTexture[texture]
			outputFile.write('%s\t1.0 1.0\t%s\t%s\t%s\n' % (texture, format_textcoord(uvsForFace[i][0]), format_textcoord(uvsForFace[i][1]), format_textcoord(uvsForFace[i][2])))
	outputFile.write('\n')
	
	# Write NAMES section if used (textures in place and not pretty printing)
	if len(names_lines_out) != 0:
		outputFile.write('NAMES %u\n' % len(names_lines_out))
		outputFile.writelines(names_lines_out)
		outputFile.write('\n')
	
	outputFile.writelines(normals_lines_out)
	outputFile.write('\n')
	outputFile.write('END\n')
	outputFile.close()
	inputFile.close()


print 'Done.\n'
