# Oolite Mesh Converters #

A set of Python scripts to convert models to and from Oolite’s DAT format.

The tools are:

*Obj2DatTexNorm.py*: convert a mesh in OBJ format to DAT, preserving texture coordinates and vertex normals. This is now the recommended conversion tool. The meshes it produces require Oolite test release 1.74 or later.

From a Wings3D modelling perspective, preserving vertex normals means that hard and soft edges in Wings3D are preserved, producing a result similar to Wings3D preview mode (Tab key) if all the faces in Wings3D are planar (ensure this by selecting Tesselate → Triangulate in face mode). The smooth key in shipdata.plist has no effect on models with vertex normals.

Usage: `python Obj2DatTexNorm.py <filename>` for default settings, `python Obj2DatTexNorm.py --help` for information about options.


*Obj2DatTex.py*: an older conversion tool which does not preserve normals but does support smooth groups. Models converted with this tool will have a faceted look by default, but can be smoothed using the smooth key in shipdata.plist.

From a Wings3D modelling perspective, complete loops of hard edges will be preserved when using smoothing (the enclosed faces form a smooth group), but lighting may behave differently than in Wings3D preview mode.

Usage: `python Obj2DatTex.py <filename>`


*Dat2ObjTex.py* and *Dat2Obj.py*: partially convert a DAT mesh to OBJ format. Dat2ObjTex.py can handle a single material, while Dat2Obj.py ignores all textures. These tools do not preserve normals, and Dat2ObjTex.py won’t do anything useful with materials from files converted with Obj2DatTexNorm.py unless `--pretty-output` was used.

Usage: `python Dat2ObjTex.py <filename>`, `python Dat2Obj.py <filename>`


*DatScale.py*: scale a DAT model uniformly on all axes.

Usage: `python DatScale.py <filename> <scalefactor>`, e.g. `python DatScale.py myModel.dat 3`. A new file is created, in the example case “myModel x 3.0.dat”.


*Mesh2Dat.py*, *Mesh2DatTex.py*, *Dat2Mesh.py*, *Mesh2Obj.py*: converters for the obsolete, Mac-specific Meshwork modeller.


The converters require Python (version 2.7 or later for Obj2DatTexNorm.py). Mac OS X and Linux systems generally have Python preinstalled. For Linux systems, check your package manager if necessary. For Windows, download it from python.org.


Bug reports: currently, Obj2DatTexNorm.py is the only one that can be considered actively maintained, and the others have known problems. Crash/exception reports for all tools are welcomed, as well as reports of bad conversions with Obj2DatTexNorm.py. In order for reports to be useful, please ensure that they apply to the latest version – the link at the top of this post is always up-to-date – and include, at minimum, a copy of the file you’re trying to convert (and its associated MTL file in the case of OBJ files).
