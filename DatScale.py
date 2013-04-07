#!/usr/bin/python 

""" 
This script takes an Oolite .dat file, scales it by a specified scale factor,
and writes it out again (appending the scale factor to the name).

Only the VERTEX section is modified. The rest of the file is passed through
unchanged.
""" 

import sys, string, math, re


class DATLexer:
	""" Tokens scanner for DAT files. """
	def __init__(self, data):
		self.__data = data
		self.__end = len(data)
		self.__cursor = 0
		self.__tokenLength = 0
		self.__lineNumber = 1
		self.__lastSeparator = ""
		self.__isSeparatorChar = re.compile(r"[\ \r\n\t,]")
		self.__isLineEnd = re.compile(r"[\r\n]")
		self.__isNotLineEnd = re.compile(r"[^\r\n]")
		self.__lastIsCR = False
	
	def lineNumber(self):
		""" Returns the line number at the beginning of the current token. """
		return self.__lineNumber
	
	def currentToken(self):
		""" Returns the current token. """
		return self.__currentToken
		
	def lastSeparator(self):
		""" Returns the non-token content between the current token and the previous token. """
		return self.__lastSeparator
	
	def nextToken(self):
		""" Reads the next token. """
		self.__advance(False)
		return self.currentToken()
	
	def expectLiteral(self, literal):
		""" Reads a token and checks whether it matches the expected string. """
		return self.nextToken() == literal
	
	def readInt(self):
		""" Reads an integer. """
		self.__advance(False)
		return int(self.currentToken())
	
	def readFloat(self):
		""" Reads a floating-point number. """
		self.__advance(False)
		return float(self.currentToken())
	
	def readUntilNewLine(self):
		""" Reads until the beginning of a new line or the beginning of a comment. """
		sef.__advance(True)
		return self.currentToken()
		
	def atEnd(self):
		""" Tests whether the lexer has reached the end of its data. """
		return self.__cursor == self.__end
	
	
	def __advance(self, untilEOL):
		self.__cursor += self.__tokenLength
		assert self.__cursor < self.__end
		initialCursor = self.__cursor
		
		# Find beginning of token.
		while 1:
			self.__skipWhile(self.__isSeparatorChar)
			
			if not self.atEnd() and self.__commentAt(self.__cursor):
				self.__skipWhile(self.__isNotLineEnd)
			else:
				break
		
		self.__lastSeparator = self.__data[initialCursor:self.__cursor]
		
		# Find length of token.
		endCursor = None
		if untilEOL:
			endCursor = self.__scanTokenLength(self.__isLineEnd)
		else:
			endCursor = self.__scanTokenLength(self.__isSeparatorChar)
		
		self.__tokenLength = endCursor - self.__cursor
		self.__currentToken = self.__data[self.__cursor:endCursor]
	
	
	def __skipWhile(self, matcher):
		while 1:
			if self.__cursor == self.__end:
				return
			
			curr = self.__data[self.__cursor]
			if not matcher.match(curr):
				return
			
			if self.__isNotLineEnd.match(curr):
				self.__lastIsCR = False
			else:
				if curr != '\n' or not self.__lastIsCR:
					self.__lineNumber = self.__lineNumber + 1
				self.__lastIsCR = curr == '\r'
			
			self.__cursor = self.__cursor + 1
	
	def __scanTokenLength(self, endCriterion):
		endCursor = self.__cursor + 1
		while endCursor < self.__end and not endCriterion.match(self.__data[endCursor]) and not self.__commentAt(endCursor):
			endCursor = endCursor + 1
		return endCursor
	
	def __commentAt(self, offset):
		if self.__data[offset] == '#':
			return True
		if offset + 1 < self.__end and self.__data[offset] == '/' and self.__data[offset + 1] == '/':
			return True
		return False
	

if len(sys.argv) != 3:
	print "Expected two arguments, file name and scale factor."
	exit(1)

inputFileName = sys.argv[1]
factor = float(sys.argv[2])

outputFileName = ""
outputFileComponents = inputFileName.rsplit(".", 1)
if len(outputFileComponents) == 1 or outputFileComponents[1].lower() != "dat":
	outputFileName = inputFileName
else:
	outputFileName = outputFileComponents[0]

outputFileName += " x " + str(factor) + ".dat";

print "Scaling \"" + inputFileName + "\" by " + str(factor) + " to \"" + outputFileName + "\"..."

nVerts = 0
inputFile = open(inputFileName, "r")
fileData = inputFile.read()
lexer = DATLexer(fileData)

lexer.expectLiteral("NVERTS")
nverts = lexer.readInt()
lexer.expectLiteral("NFACES")
nfaces = lexer.readInt()
lexer.expectLiteral("VERTEX")

outputFile = open(outputFileName, "w")
outputFile.write("// " + inputFileName + " rescaled by a factor of " + str(factor) + "\n\n")
outputFile.write("NVERTS " + str(nverts) + "\nNFACES " + str(nfaces) + "\n\nVERTEX\n");


for i in range(nverts):
	x = lexer.readFloat() * factor
	y = lexer.readFloat() * factor
	z = lexer.readFloat() * factor
	
	outputFile.write('% 5f,% .5f,% .5f\n' % (x, y, z))
	#outputFile.write(str(x * factor) + ", " + str(y * factor) + ", " + str(z * factor) + "\n")


while not lexer.atEnd():
	token = lexer.nextToken();
	outputFile.write(lexer.lastSeparator())
	outputFile.write(token)
