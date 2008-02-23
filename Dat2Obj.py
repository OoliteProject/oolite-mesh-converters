#!/usr/bin/python

"""
This script takes a .dat file from the Elite/Oolite source
and exports a .obj file containing the same geometry.

Material for the faces is set to flat white (127,127,127)
and surface normals need not be calculated.
"""

import sys, string, math

inputfilenames = sys.argv[1:]
print "converting..."
print inputfilenames
for inputfilename in inputfilenames:
	outputfilename = inputfilename.lower().replace(".dat",".obj")
	materialfilename = inputfilename.lower().replace(".dat",".mtl")
	mtllibname = string.split(materialfilename, "/")[-1]
	objname=mtllibname.replace(".mtl","")
	print inputfilename+"->"+outputfilename+" & "+materialfilename
	inputfile = open(inputfilename,"r")
	lines = inputfile.read().splitlines(0)
	
	mode = 'SKIP'
	vertex_lines_out = []
	faces_lines_out = ['g '+objname+'_default\n']
	faces_lines_out.append ('usemtl default')
	
	n_verts = 0
	n_faces = 0
	skips = 0
	vertex=[]

	for line in lines:
		if (mode == 'VERTEX'):
			coordinates = string.split(line, ',')	# split line by commas
			if (len(coordinates) == 3):
				n_verts = n_verts + 1
				x = -float(coordinates[0])
				y = float(coordinates[1])
				z = float(coordinates[2])
				vertex.append( (x, y, z) )
				vertex_lines_out.append('v %.5f %.5f %.5f\n' % ( x, y, z))
				vertex.append( (x, y, z ) )
		elif (mode == 'FACES'):
			tokens = string.split(line, ',')	# split line by commas
			if (len(tokens) > 9) :
				color_data = tokens[0:3]
				normal_data =tokens[3:6]
				n_points = tokens[6]
				point_data = tokens[7:]
				n_faces = n_faces + 1
				
				faces_lines_out.append ('\nf ')
				for i in range( 0,int(n_points)) :
					faces_lines_out.append ('%i// ' % (int(point_data[i])+1))
				#
				
		elif (mode == 'SKIP'):
			skips = skips + 1
		#
		if (line[:6] == 'NVERTS'):
			mode = 'SKIP'
		if (line[:6] == 'NFACES'):
			mode = 'SKIP'
		if (line[:6] == 'VERTEX'):
			mode = 'VERTEX'
		if (line[:5] == 'FACES'):
			mode = 'FACES'
		#
	outputfile = open(outputfilename,"w")
	outputfile.write('# Exported with Dat2Obj.py (C) Giles Williams 2005 - Kaks 2008\n')
	outputfile.write('mtllib %s\n' % mtllibname)
	outputfile.write('o '+objname+'\n')
	outputfile.write('# %d vertices,' % n_verts) 
	outputfile.write(' %d faces\n' % n_faces) 
	outputfile.writelines(vertex_lines_out)
	outputfile.writelines(faces_lines_out)
	outputfile.writelines('\n\n')
	outputfile.close();
	materialfile = open(materialfilename,"w")
	materialfile.write(	'# Exported with Dat2Obj.py (C) Giles Williams 2005 - Kaks 2008\n')
	materialfile.write(	'newmtl default\nNs 100.000\n')
	materialfile.write(	'd 1.00000\nillum 2\n')
	materialfile.write(	'MATERIAL\t65535\t0\t0\t0\t0\t0\n')
	materialfile.write(	'Kd 1.00000 1.00000 1.00000\nKa 1.00000 1.00000 1.00000\n')
	materialfile.write(	'Ks 1.00000 1.00000 1.00000\nKe 0.00000e+0 0.00000e+0 0.00000e+0\n\n')
	materialfile.close();

print "done"
print ""
#
#	end
#
