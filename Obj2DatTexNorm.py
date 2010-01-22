#!/usr/bin/python

# EXTENSIONS  : "obj" "OBJ"					# Accepted file extentions
# OSTYPES     : "****"						# Accepted file types
# ROLE        : Editor						# Role (Editor, Viewer, None)
# SERVICEMENU : Obj2DatTex/Convert to .dat	# Name of Service menu item

"""
This script takes a Wavefront .obj file
and exports a .dat file containing the same trimesh.

This version generates files with per-vertex normals, for Oolite 1.74 and later
only.
"""


include_face_normals	= 0		# If 1, per-face normals are generated for Oolite 1.73 and earlier. If 0, file is smaller.
pretty_output			= 0		# If 0, optimize for size and loading speed. If 1, use more legible format.


import sys, string, math

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
	"""
	result = ('%.5f' % n).rstrip('.0')
	if result == "":
		return "0"
	else:
		return result


def format_vertex(v):
	if pretty_output:
		return '% .5f,% .5f,% .5f' % v
	else:
		x, y, z = v
		return '%s %s %s' % (format_number(x), format_number(y), format_number(z))


def format_textcoord(st):
	if pretty_output:
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
		normals_lines_out.append(format_vertex(vn) + '\n')
		
		return result


def normalize(n):
	""" normalize
		Normalize a vector, specified as a tuple of three components.
	"""
	x, y, z = n
	scale = 1.0 / math.sqrt(x * x + y * y + z * z)
	return x * scale, y * scale, z * scale


def average_normal(n1, n2, n3):
	""" average_normal
		Calculate the normalized sum of three vectors.
	"""
	x1, y1, z1 = n1
	x2, y2, z2 = n2
	x3, y3, z3 = n3
	return normalize((x1 + x2 + x3, y1 + y2 + y3, z1 + z2 + z3))


inputfilenames = sys.argv[1:]
print "converting..."
print inputfilenames
for inputfilename in inputfilenames:
	outputfilename = inputfilename.lower().replace(".obj", ".dat")
	if (outputfilename == inputfilename):
		outputfilename = outputfilename,append(".1")
	print inputfilename+"->"+outputfilename
	inputfile = open( inputfilename, "r")
	lines = inputfile.read().splitlines(0)
	outputfile = open( outputfilename, "w")
	mode = 'SKIP'
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
	# find materials from mtllib
	for line in lines:
		tokens = string.split(line)
		#print "line :"
		#print line
		#print "tokens :"
		#print tokens
		if tokens != []:
			if tokens[0] == 'mtllib':
				path = string.split(inputfilename, '/')
				path[-1] = tokens[1]
				materialfilename = string.join(path,'/')
				print "going to open material library file: %s" % materialfilename
				infile = open( materialfilename, "r")
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
								print "Material %s -> %s" % (newMaterialName, name)
								if pretty_output:
									materials[newMaterialName] = name
								else:
									index = len(materials)
									materials[newMaterialName] = index
									names_lines_out.append(name + '\n')
							newMaterial = 0
	#print "materials :"
	#print materials
	# find geometry vertices first
	for line in lines:
		tokens = string.split(line)
		if tokens != []:
			if tokens[0] == 'v':
				n_verts = n_verts + 1
				# negate x value for vertex to allow correct texturing...
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
				#print "line: %s" % line
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
							print "File does not provide texture coordinates! Materials will not be exported."
						interpretTexture = 0
					if (bits[2] > ''):
						vn3 = vertex_reference(int(bits[2]), n_normals)
					
					#print "face (geometry): %d %d %d" % (v1, v2, v3)
					#print "face (textures): %d %d %d\n" % (vt1, vt2, vt3)
					d0 = (vertex[v2][0] - vertex[v1][0], vertex[v2][1] - vertex[v1][1], vertex[v2][2] - vertex[v1][2])
					d1 = (vertex[v3][0] - vertex[v2][0], vertex[v3][1] - vertex[v2][1], vertex[v3][2] - vertex[v2][2])
					xp = (d0[1] * d1[2] - d0[2] * d1[1], d0[2] * d1[0] - d0[0] * d1[2], d0[0] * d1[1] - d0[1] * d1[0])
					det = math.sqrt(xp[0]*xp[0] + xp[1]*xp[1] + xp[2]*xp[2])
					if (det > 0):
						rv1 = resolve_vertex(vertex[v1], normal[vn1], index_for_vert_and_norm, vertex_lines_out, normals_lines_out)
						rv2 = resolve_vertex(vertex[v2], normal[vn2], index_for_vert_and_norm, vertex_lines_out, normals_lines_out)
						rv3 = resolve_vertex(vertex[v3], normal[vn3], index_for_vert_and_norm, vertex_lines_out, normals_lines_out)
						
						if not include_face_normals:
							face_normal_str = '0 0 0'
						else:
							face_normal_str = format_vertex(average_normal(normal[vn1], normal[vn2], normal[vn3]))
						
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
	# begin final output...
	outputfile.write('// output from Obj2DatTexNorm.py Wavefront text file conversion script\n')
	outputfile.write('// (c) 2005-2010 By Giles Williams and Jens Ayton\n')
	outputfile.write('// \n')
	outputfile.write('// original file: "%s"\n' % inputfilename)
	outputfile.write('// \n')
	outputfile.write('// model size: %.3f x %.3f x %.3f\n' % ( max_v[0]-min_v[0], max_v[1]-min_v[1], max_v[2]-min_v[2]))
	outputfile.write('// \n')
	outputfile.write('// materials used: %s\n' % materials_used)
	outputfile.write('// \n')
	outputfile.write('NVERTS %d\n' % resolved_vertex_count)
	outputfile.write('NFACES %d\n' % n_faces)
	outputfile.write('\n')
	outputfile.writelines(vertex_lines_out)
	outputfile.write('\n')
	outputfile.writelines(faces_lines_out)
	outputfile.write('\n')
	# check that we have textures for every vertex...
	okayToWriteTexture = 1
	#print "uvsForTexture :"
	#print uvsForTexture
	#print "uvsForFace :"
	#print uvsForFace
	if (len(textureForFace) != len(face)):
		okayToWriteTexture = 0
	if (len(uvsForFace) != len(face)):
		okayToWriteTexture = 0
	for texture in textureForFace:
		if (texture == ''):
			okayToWriteTexture = 0
	# if we're all clear then write out the texture uv coordinates
	if (okayToWriteTexture):
		outputfile.write('TEXTURES\n')
		for i in range(0, len(face)):
			facet = face[i]
			texture = textureForFace[i]
			uvForVertex = uvsForTexture[texture]
			outputfile.write('%s\t1.0 1.0\t%s\t%s\t%s\n' % (texture, format_textcoord(uvsForFace[i][0]), format_textcoord(uvsForFace[i][1]), format_textcoord(uvsForFace[i][2])))
	outputfile.write('\n')
	
	if len(names_lines_out) != 0:
		outputfile.write('NAMES %u\n' % len(names_lines_out))
		outputfile.writelines(names_lines_out)
		outputfile.write('\n')
	
	outputfile.writelines(normals_lines_out)
	outputfile.write('\n')
	outputfile.write('END\n')
	outputfile.close();

print "done"
print ""
#
#	end
#
