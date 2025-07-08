import bpy

class MaterialNodesCompiler:
	"""
	Enhanced version of the Blender GLSL translator with addon integration
	
	Limitations:
		- "Material Output" only supports the "Surface" input
		- Only the first "Material Output" node is used if there are multiple
		- "Material Output" nodes inside group nodes will not be used
		- "Add Shader" is allowed to use but implemented as "Mix Shader" with factor 0.5
		
	Currently translateable nodes:
		+ Input -> Value
		+ Input -> RGB
		+ Texture -> Image Texture
		+ Texture -> Noise Texture
		+ Color -> Bright Contrast
		+ Color -> Gamma
		+ Color -> Mix RGB (Hue, Saturation, Color and Value are not supported)
		+ Vector -> Normal Map
		+ Converter -> Combine HSV/RGB/XYZ
		+ Converter -> Map Range
		+ Converter -> Math
		+ Converter -> RGB to BW
		+ Converter -> Separate HSV/RGB/XYZ
		+ Converter -> Vector Math (Snap is not supported)
		+ Group
		(Not listed nodes may be useable, but without full functionality)
		
	"""
	def __init__(self, nodeTree):
		# forceValidTranslation is default true
		# if a node is not supported or somehow else an error occurs, the compiler would complain about the error
		# however forceValidTranslation will give the compiler a default value instead to work with
		# it also puts error information in comment tags in the translated output
		# note: it will not correct somehow magically bad glsl output, so even with forceValidTranslation there may be compiler errors
		# set forceValidTranslation to False to make the compiler cry for translation errors
		self.forceValidTranslation = True
		self.debugOutputToConsole = False  # Changed for addon use
		self.finalOutputToConsole = False
		self.compiler = 'glslc %INFILE% -o %OUTFILE%'
		self.varPrefix = 'var'
		self.floatFormat = '{0:.5f}'
		self.inputs = {}
		self.uniforms = {}
		self.inputs['v_position'] = {'location':0, 'type':'vec3', 'nodes':'NEW_GEOMETRY@Position'}
		self.inputs['v_normal'] = {'location':1, 'type':'vec3', 'nodes':'NEW_GEOMETRY@Normal'}
		self.inputs['v_objectNormal'] = {'location':2, 'type':'vec3', 'nodes':'TEX_COORD@Normal'}
		self.inputs['v_texCoord'] = {'location':3, 'type':'vec2', 'nodes':'TEX_COORD@UV'}
		self.uniforms['v_textures'] = {'binding':0, 'type':'sampler2D[]', 'key':'GLSL@Textures'}
		self.uniforms['u_time'] = {'binding':1, 'type':'float', 'key':'GLSL@Time'}
		self.uniforms['u_frame'] = {'binding':2, 'type':'float', 'key':'GLSL@Frame'}
		self.materialStruct = {}
		self.materialStruct['color'] = {'type':'vec4', 'default':'vec4(0.8,0.8,0.8,1.0)'}
		self.materialStruct['metallic'] = {'type':'float', 'default':'0.0'}
		self.materialStruct['specular'] = {'type':'vec4', 'default':'vec4(0.5,0.5,0.5,1.0)'}
		self.materialStruct['roughness'] = {'type':'float', 'default':'0.5'}
		self.materialStruct['ior'] = {'type':'float', 'default':'1.45'}
		self.materialStruct['emission'] = {'type':'vec4', 'default':'vec4(0.0,0.0,0.0,1.0)'}
		self.materialStruct['alpha'] = {'type':'float', 'default':'1.0'}
		self.materialStruct['normal'] = {'type':'vec3', 'default':'vec3(0.0,0.0,0.0)'}
		self.materialDefault = 'material('+(','.join([v['default'] for k,v in self.materialStruct.items()]))+')'
		self.functions = {}
		self.functions['mixMaterial'] = {'require':[], 'func':'material mixMaterial(material a, material b, float f) {return material('+(','.join([('mix(a.'+k+',b.'+k+',f)') for k in self.materialStruct]))+');}'}
		self.functions['mapRange'] = {'require':[], 'func':'float mapRange(float v, float fromMin, float fromMax, float toMin, float toMax) {return toMin+(toMax-toMin)*((v-fromMin)/(fromMax-fromMin));}'}
		self.functions['mapRangeClamp'] = {'require':['mapRange'], 'func':'float mapRangeClamp(float v, float fromMin, float fromMax, float toMin, float toMax) {return clamp(mapRange(v,fromMin,fromMax,toMin,toMax),toMin,toMax);}'}
		self.functions['vectorProject'] = {'require':[], 'func':'vec3 vectorProject(vec3 a, vec3 b) {return dot(a,b)/dot(b,b)*b;}'}
		self.functions['colorMixDarken'] = {'require':[], 'enum':'DARKEN', 'func':'vec4 colorMixDarken(vec4 a, vec4 b, float f) {return mix(a,min(a,b),f);}'}
		self.functions['colorMixMultiply'] = {'require':[], 'enum':'MULTIPLY', 'func':'vec4 colorMixMultiply(vec4 a, vec4 b, float f) {return mix(a,a*b,f);}'}
		self.functions['colorMixBurn'] = {'require':[], 'enum':'BURN', 'func':'vec4 colorMixBurn(vec4 a, vec4 b, float f) {return mix(a,1.0-((1.0-a)/(b+vec4(0.0001))),f);}'}
		self.functions['colorMixLighten'] = {'require':[], 'enum':'LIGHTEN', 'func':'vec4 colorMixLighten(vec4 a, vec4 b, float f) {return mix(a,max(a,b),f);}'}
		self.functions['colorMixScreen'] = {'require':[], 'enum':'SCREEN', 'func':'vec4 colorMixScreen(vec4 a, vec4 b, float f) {return mix(a,1.0-((1.0-a)*(1.0-b)),f);}'}
		self.functions['colorMixDodge'] = {'require':[], 'enum':'DODGE', 'func':'vec4 colorMixDodge(vec4 a, vec4 b, float f) {return mix(a,min(a/(1.0001-b),vec4(1.0)),f);}'}
		self.functions['colorMixAdd'] = {'require':[], 'enum':'ADD', 'func':'vec4 colorMixAdd(vec4 a, vec4 b, float f) {return mix(a,min(a+b,vec4(1.0)),f);}'}
		self.functions['colorMixOverlayC'] = {'require':[], 'func':'float colorMixOverlayC(float a, float b) {return (a<0.5)?(2.0*b*a):(1.0-2.0*(1.0-a)*(1.0-b));}'}
		self.functions['colorMixOverlay'] = {'require':['colorMixOverlayC'], 'enum':'OVERLAY', 'func':'vec4 colorMixOverlay(vec4 a, vec4 b, float f) {return mix(a,vec4(colorMixOverlayC(a.r,b.r),colorMixOverlayC(a.g,b.g),colorMixOverlayC(a.b,b.b),colorMixOverlayC(a.a,b.a)),f);}'}
		self.functions['colorMixSoftLightC'] = {'require':[], 'func':'float colorMixSoftLightC(float a, float b) {return (b<0.5)?(1.0*a*b+a*a*(1.0-2.0*b)):(sqrt(a)*(2.0*b-1.0)+2.0*a*(1.0-b));}'}
		self.functions['colorMixSoftLight'] = {'require':['colorMixSoftLightC'], 'enum':'SOFT_LIGHT', 'func':'vec4 colorMixSoftLight(vec4 a, vec4 b, float f) {return mix(a,vec4(colorMixSoftLightC(a.r,b.r),colorMixSoftLightC(a.g,b.g),colorMixSoftLightC(a.b,b.b),colorMixSoftLightC(a.a,b.a)),f);}'}
		self.functions['colorMixLinearLightC'] = {'require':[], 'func':'float colorMixLinearLightC(float a, float b) {return (b<0.5)?max(a+(2.0*b)-1.0,0.0):min(a+(2.0*(b-0.5)),1.0);}'}
		self.functions['colorMixLinearLight'] = {'require':['colorMixLinearLightC'], 'enum':'LINEAR_LIGHT', 'func':'vec4 colorMixLinearLight(vec4 a, vec4 b, float f) {return mix(a,vec4(colorMixLinearLightC(a.r,b.r),colorMixLinearLightC(a.g,b.g),colorMixLinearLightC(a.b,b.b),colorMixLinearLightC(a.a,b.a)),f);}'}
		self.functions['colorMixDifference'] = {'require':[], 'enum':'DIFFERENCE', 'func':'vec4 colorMixDifference(vec4 a, vec4 b, float f) {return mix(a,abs(a-b),f);}'}
		self.functions['colorMixSubtract'] = {'require':[], 'enum':'SUBTRACT', 'func':'vec4 colorMixSubtract(vec4 a, vec4 b, float f) {return mix(a,max(a+b-1.0,vec4(0.0)),f);}'}
		self.functions['colorMixDivide'] = {'require':[], 'enum':'DIVIDE', 'func':'vec4 colorMixDivide(vec4 a, vec4 b, float f) {return mix(a,(1.0-a)/(b+0.0001),f);}'}
		self.functions['brightnessContrast'] = {'require':[], 'func':'vec4 brightnessContrast(vec4 color, float bright, float cont) {return vec4((color.rgb-0.5)*cont+0.5+bright,color.a);}'}
		self.functions['gamma'] = {'require':[], 'func':'vec4 gamma(vec4 color, float gamma) {return vec4(pow(color.rgb,vec3(1.0/gamma)),color.a);}'}
		self.functions['rgb2bw'] = {'require':[], 'func':'float rgb2bw(vec4 c) {return (c.r+c.g+c.b)/3.0;}'}
		self.functions['rgb2hsv'] = {'require':[], 'func':'vec3 rgb2hsv(vec3 c) {vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0); vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g)); vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r)); float d = q.x - min(q.w, q.y); float e = 1.0e-10; return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);}'}
		self.functions['hsv2rgb'] = {'require':[], 'func':'vec3 hsv2rgb(vec3 c) {vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0); vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www); return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);}'}
		self.functions['buildTransform'] = {'require':[], 'func':'mat4 buildTransform(vec3 l, vec3 r, vec3 s) {vec3 a=sin(r); vec3 b=cos(r); return mat4(vec4(b.y*b.z+a.x*a.z*s.x,b.y*a.z-a.x*a.y*b.z,b.x*a.y,0.0),vec4(-b.x*a.z,b.x*b.z*s.y,a.x,0.0),vec4(a.x*b.y*a.z-a.y*b.z,-a.y*a.z-a.x*b.y*b.z,b.x*b.y*s.z,0.0),vec4(l.xyz,1.0));}'}
		self.functions['mapping'] = {'require':['buildTransform'], 'func':'vec3 mapping(vec3 vec, vec3 loc, vec3 rot, vec3 sca) {return (vec4(vec,1.0)*buildTransform(loc,rot,sca)).xyz;}'}
		
		# Noise functions for procedural textures
		self.functions['hash'] = {'require':[], 'func':'float hash(vec2 p) {return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);}'}
		self.functions['hash3d'] = {'require':[], 'func':'float hash3d(vec3 p) {return fract(sin(dot(p, vec3(127.1, 311.7, 74.7))) * 43758.5453123);}'}
		self.functions['hash4d'] = {'require':[], 'func':'float hash4d(vec4 p) {return fract(sin(dot(p, vec4(127.1, 311.7, 74.7, 269.5))) * 43758.5453123);}'}
		self.functions['noise2d'] = {'require':['hash'], 'func':'float noise2d(vec2 p) {vec2 i = floor(p); vec2 f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(hash(i + vec2(0.0, 0.0)), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);}'}
		self.functions['noise3d'] = {'require':['hash3d'], 'func':'float noise3d(vec3 p) {vec3 i = floor(p); vec3 f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(mix(hash3d(i + vec3(0.0, 0.0, 0.0)), hash3d(i + vec3(1.0, 0.0, 0.0)), f.x), mix(hash3d(i + vec3(0.0, 1.0, 0.0)), hash3d(i + vec3(1.0, 1.0, 0.0)), f.x), f.y), mix(mix(hash3d(i + vec3(0.0, 0.0, 1.0)), hash3d(i + vec3(1.0, 0.0, 1.0)), f.x), mix(hash3d(i + vec3(0.0, 1.0, 1.0)), hash3d(i + vec3(1.0, 1.0, 1.0)), f.x), f.y), f.z);}'}
		self.functions['noise4d'] = {'require':['hash4d'], 'func':'float noise4d(vec4 p) {vec4 i = floor(p); vec4 f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(mix(mix(hash4d(i + vec4(0.0, 0.0, 0.0, 0.0)), hash4d(i + vec4(1.0, 0.0, 0.0, 0.0)), f.x), mix(hash4d(i + vec4(0.0, 1.0, 0.0, 0.0)), hash4d(i + vec4(1.0, 1.0, 0.0, 0.0)), f.x), f.y), mix(mix(hash4d(i + vec4(0.0, 0.0, 1.0, 0.0)), hash4d(i + vec4(1.0, 0.0, 1.0, 0.0)), f.x), mix(hash4d(i + vec4(0.0, 1.0, 1.0, 0.0)), hash4d(i + vec4(1.0, 1.0, 1.0, 0.0)), f.x), f.y), f.z), mix(mix(mix(hash4d(i + vec4(0.0, 0.0, 0.0, 1.0)), hash4d(i + vec4(1.0, 0.0, 0.0, 1.0)), f.x), mix(hash4d(i + vec4(0.0, 1.0, 0.0, 1.0)), hash4d(i + vec4(1.0, 1.0, 0.0, 1.0)), f.x), f.y), mix(mix(hash4d(i + vec4(0.0, 0.0, 1.0, 1.0)), hash4d(i + vec4(1.0, 0.0, 1.0, 1.0)), f.x), mix(hash4d(i + vec4(0.0, 1.0, 1.0, 1.0)), hash4d(i + vec4(1.0, 1.0, 1.0, 1.0)), f.x), f.y), f.z), f.w);}'}
		self.functions['fbm2d'] = {'require':['noise2d'], 'func':'float fbm2d(vec2 p, int octaves) {float value = 0.0; float amplitude = 0.5; for (int i = 0; i < 8; i++) {if (i >= octaves) break; value += amplitude * noise2d(p); p *= 2.0; amplitude *= 0.5;} return value;}'}
		self.functions['fbm3d'] = {'require':['noise3d'], 'func':'float fbm3d(vec3 p, int octaves) {float value = 0.0; float amplitude = 0.5; for (int i = 0; i < 8; i++) {if (i >= octaves) break; value += amplitude * noise3d(p); p *= 2.0; amplitude *= 0.5;} return value;}'}
		self.functions['fbm4d'] = {'require':['noise4d'], 'func':'float fbm4d(vec4 p, int octaves) {float value = 0.0; float amplitude = 0.5; for (int i = 0; i < 8; i++) {if (i >= octaves) break; value += amplitude * noise4d(p); p *= 2.0; amplitude *= 0.5;} return value;}'}
		self.functions['noiseTexture'] = {'require':['fbm3d'], 'func':'float noiseTexture(vec3 coord, float scale, float detail, float roughness) {vec3 p = coord * scale; int octaves = int(clamp(detail, 1.0, 8.0)); return fbm3d(p, octaves);}'}
		self.functions['noiseTexture4D'] = {'require':['fbm4d'], 'func':'float noiseTexture4D(vec3 coord, float w, float scale, float detail, float roughness) {vec4 p = vec4(coord, w) * scale; int octaves = int(clamp(detail, 1.0, 8.0)); return fbm4d(p, octaves);}'}
		self.functions['voronoiTexture'] = {'require':['hash3d'], 'func':'float voronoiTexture(vec3 coord, float scale, float smoothness, float exponent, float randomness) {\n\tvec3 p = coord * scale;\n\tvec3 i = floor(p);\n\tvec3 f = fract(p);\n\tfloat minDist = 1.0;\n\tfor(int x = -1; x <= 1; x++) {\n\t\tfor(int y = -1; y <= 1; y++) {\n\t\t\tfor(int z = -1; z <= 1; z++) {\n\t\t\t\tvec3 neighbor = vec3(float(x), float(y), float(z));\n\t\t\t\tvec3 cellPoint = i + neighbor;\n\t\t\t\tvec3 cellOffset = vec3(hash3d(cellPoint + vec3(0.0)), hash3d(cellPoint + vec3(1.0)), hash3d(cellPoint + vec3(2.0))) * randomness;\n\t\t\t\tvec3 pointPos = neighbor + cellOffset;\n\t\t\t\tfloat dist = length(pointPos - f);\n\t\t\t\tminDist = min(minDist, dist);\n\t\t\t}\n\t\t}\n\t}\n\treturn smoothstep(0.0, 1.0, minDist);\n}'}
		
		for k,v in self.functions.items():
			v['name'] = k
			v['returnType'] = v['func'].split(' ',1)[0]
		self.nodeTree = nodeTree
	
	def compile(self):
		import tempfile
		from os import path
		import shutil
		import subprocess
		translation = self.translate()
		tmpdir = tempfile.mkdtemp()
		srcFilepath = path.join(tmpdir, 'material.frag')
		dstFilepath = path.join(tmpdir, 'material.frag.spv')
		srcFile = open(srcFilepath, "w")
		srcFile.write(translation)
		srcFile.close()
		command = self.compiler
		command = command.replace('%INFILE%', '"'+srcFilepath+'"')
		command = command.replace('%OUTFILE%', '"'+dstFilepath+'"')
		p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		self.compileOutput = ''
		for l in p.stdout.readlines():
			self.compileOutput += str(l)+'\n'
		print(self.compileOutput)
		shutil.rmtree(tmpdir)
		return translation
		
	def translate(self):
		self.errors = []
		self.vars = []
		self.useFunctions = []
		self.textures = []
		# may be counter intuitive, but the parsing starts at the output and goes back all the nodes in the tree
		startNode = None
		for node in self.nodeTree.nodes:
			if node.type == 'OUTPUT_MATERIAL' and node.inputs.get('Surface') and node.inputs.get('Surface').is_linked:
				startNode = node
				break
		if startNode is None:
			self.error = True
			if self.forceValidTranslation:
				v = self.virtualVar('material', 'mat', 0, self.materialDefault)
				v['value'] = self.errorValue('material', 'START_NODE_NOT_FOUND()', v)
				self.vars = [v]
			else:
				return 'START_NODE_NOT_FOUND()'
		else:
			self.translateNode(startNode)
		# at this point the required nodes should be translated, however it is possible that some translated nodes are in the wrong order
		# this can happen if a node output is already translated for a nodes input, but used later again by another node
		# therefore translateNodeOutput adds the 'required' entry
		oVars = []
		for v in self.vars:
			v['sorted'] = False
		while len(oVars)!=len(self.vars):
			for v in self.vars:
				if v['sorted']==True:
					continue
				skip = False
				for r in v['required']:
					if r['sorted']==False:
						skip = True
						break
				if skip==False:
					v['sorted'] = True
					oVars.append(v)
		self.vars = oVars
		
		#todo: vars that only have 1 use (len(self.vars[i]['required'])) don't need their own assignment to improve the glsl code
		
		o = '#version 440\n\n'
		# write material struct
		o += 'struct material\n{\n'
		for k,v in self.materialStruct.items():
			o += '\t'+v['type']+' '+k+';\n'
		o += '};\n\n'
		
		# write shader inputs
		for k,v in self.inputs.items():
			o += 'layout(location='+str(v['location'])+') in '+v['type']+' '+k+';\n'
		# write shader uniforms
		for k,v in self.uniforms.items():
			if '[]' in v['type']:
				t = v['type'].replace('[]', '')
				if v['key']=='GLSL@Textures' and len(self.textures)>0:
					o += 'uniform '+t+' '+k+'['+str(len(self.textures))+'];\n'
			else:
				o += 'uniform '+v['type']+' '+k+';\n'
		o += 'layout(location=0) out vec4 fragColor;\n'
		o += '\n'
		
		# write functions required
		for f in self.useFunctions:
			o += f['func']+'\n'
		o += '\n'
			
		# write main function
		o += 'void main()\n{\n'
		line = len(o.split('\n'))
		dbg = o
		for var in self.vars[::-1]:
			dbg += '\033[90m'
			if 'comment' in var:
				dbg += '\n\t/* '+var['comment']+' */\n'
			else:
				dbg += '\n'
			if 'outputId' in var:
				dbg += '\t/* '+var['outputId']+' */\n'
			dbg += '\033[0m'
			if var['error']==True:
				dbg += '\033[91m'
			l = var['type']+' '+var['key']+' = '+var['value']+';\n'
			dbg += '\t\033[90m/* '+str(line)+' */\033[0m '+l
			o += '\t'+l
			if var['error']==True:
				dbg += '\033[0m'
			line += 1
			
		c = '\n'
		c += 'fragColor = vec4(mat.color.xyz, mat.alpha);\n'
		
		for l in c.split('\n'):
			o += '\t'+l+'\n'
			dbg += '\t\033[90m/* '+str(line)+' */\033[0m '+l+'\n'
			line += 1
		o += '}'
		dbg += '}\n'
		dbg += '\033[90m'
		dbg += '\n/* Translation Errors: '+str(len(self.errors))+' */'
		for err in self.errors:
			dbg += '\n/* '+err+' */'
		dbg += '\033[0m'
		if self.debugOutputToConsole:
			print('\n-----------------------\n'+dbg+'\n\n-----------------------\n')
		if self.finalOutputToConsole:
			print('\n-----------------------\n'+o+'\n\n-----------------------\n')
		return o
	
	def compile(self):
		import tempfile
		from os import path
		import shutil
		import subprocess
		translation = self.translate()
		tmpdir = tempfile.mkdtemp()
		srcFilepath = path.join(tmpdir, 'material.frag')
		dstFilepath = path.join(tmpdir, 'material.frag.spv')
		srcFile = open(srcFilepath, "w")
		srcFile.write(translation)
		srcFile.close()
		command = self.compiler
		command = command.replace('%INFILE%', '"'+srcFilepath+'"')
		command = command.replace('%OUTFILE%', '"'+dstFilepath+'"')
		p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		self.compileOutput = ''
		for l in p.stdout.readlines():
			self.compileOutput += str(l)+'\n'
		print(self.compileOutput)
		shutil.rmtree(tmpdir)
		return translation
		
	def translate(self):
		self.errors = []
		self.vars = []
		self.useFunctions = []
		self.textures = []
		# may be counter intuitive, but the parsing starts at the output and goes back all the nodes in the tree
		startNode = None
		for node in self.nodeTree.nodes:
			if node.type == 'OUTPUT_MATERIAL' and node.inputs.get('Surface') and node.inputs.get('Surface').is_linked:
				startNode = node
				break
		if startNode is None:
			self.error = True
			if self.forceValidTranslation:
				v = self.virtualVar('material', 'mat', 0, self.materialDefault)
				v['value'] = self.errorValue('material', 'START_NODE_NOT_FOUND()', v)
				self.vars = [v]
			else:
				return 'START_NODE_NOT_FOUND()'
		else:
			self.translateNode(startNode)
		# at this point the required nodes should be translated, however it is possible that some translated nodes are in the wrong order
		# this can happen if a node output is already translated for a nodes input, but used later again by another node
		# therefore translateNodeOutput adds the 'required' entry
		oVars = []
		for v in self.vars:
			v['sorted'] = False
		while len(oVars)!=len(self.vars):
			for v in self.vars:
				if v['sorted']==True:
					continue
				skip = False
				for r in v['required']:
					if r['sorted']==False:
						skip = True
						break
				if skip==False:
					v['sorted'] = True
					oVars.append(v)
		self.vars = oVars
		
		#todo: vars that only have 1 use (len(self.vars[i]['required'])) don't need their own assignment to improve the glsl code
		
		o = '#version 440\n\n'
		# write material struct
		o += 'struct material\n{\n'
		for k,v in self.materialStruct.items():
			o += '\t'+v['type']+' '+k+';\n'
		o += '};\n\n'
		
		# write shader inputs
		for k,v in self.inputs.items():
			o += 'layout(location='+str(v['location'])+') in '+v['type']+' '+k+';\n'
		# write shader uniforms
		for k,v in self.uniforms.items():
			if '[]' in v['type']:
				t = v['type'].replace('[]', '')
				if v['key']=='GLSL@Textures' and len(self.textures)>0:
					o += 'uniform '+t+' '+k+'['+str(len(self.textures))+'];\n'
			else:
				o += 'uniform '+v['type']+' '+k+';\n'
		o += 'layout(location=0) out vec4 fragColor;\n'
		o += '\n'
		
		# write functions required
		for f in self.useFunctions:
			o += f['func']+'\n'
		o += '\n'
			
		# write main function
		o += 'void main()\n{\n'
		line = len(o.split('\n'))
		dbg = o
		for var in self.vars[::-1]:
			dbg += '\033[90m'
			if 'comment' in var:
				dbg += '\n\t/* '+var['comment']+' */\n'
			else:
				dbg += '\n'
			if 'outputId' in var:
				dbg += '\t/* '+var['outputId']+' */\n'
			dbg += '\033[0m'
			if var['error']==True:
				dbg += '\033[91m'
			l = var['type']+' '+var['key']+' = '+var['value']+';\n'
			dbg += '\t\033[90m/* '+str(line)+' */\033[0m '+l
			o += '\t'+l
			if var['error']==True:
				dbg += '\033[0m'
			line += 1
			
		c = '\n'
		c += 'fragColor = vec4(mat.color.xyz, mat.alpha);\n'
		
		for l in c.split('\n'):
			o += '\t'+l+'\n'
			dbg += '\t\033[90m/* '+str(line)+' */\033[0m '+l+'\n'
			line += 1
		o += '}'
		dbg += '}\n'
		dbg += '\033[90m'
		dbg += '\n/* Translation Errors: '+str(len(self.errors))+' */'
		for err in self.errors:
			dbg += '\n/* '+err+' */'
		dbg += '\033[0m'
		if self.debugOutputToConsole:
			print('\n-----------------------\n'+dbg+'\n\n-----------------------\n')
		if self.finalOutputToConsole:
			print('\n-----------------------\n'+o+'\n\n-----------------------\n')
		return o
	
	def translateNode(self, node, outputInfo=None):
		t = node.type
		clamp = False
		if 'clamp' in node:
			clamp = node.clamp
		if 'use_clamp' in node:
			clamp = node.use_clamp
		if outputInfo is not None:
			outNode = outputInfo['nodeOutput']
			outName = outNode.name
			outType = outputInfo['type']
		if outputInfo is None:
			inputInfo = {'group':[None], 'outputInfo':None}
		else:
			inputInfo = {'group':[x for x in outputInfo['group']], 'outputInfo':outputInfo}
		
		# Inputs from vertex shader
		if outputInfo is not None:
			for k,v in self.inputs.items():
				if 'nodes' in v:
					if type(v['nodes']) is str:
						if node.type+'@'+outName==v['nodes']:
							return self.convertType(k, v['type'], outType)
					elif type(v['nodes']) is list:
						for n in v['nodes']:
							if node.type+'@'+outName==n:
								return self.convertType(k, v['type'], outType)
		
		# Output Material (--> Surface)
		if t=='OUTPUT_MATERIAL':
			inputInfo['outputInfo'] = self.virtualVar('material', 'mat', 0, self.materialDefault)
			self.vars.append(inputInfo['outputInfo'])
			inputInfo['outputInfo']['value'] = self.translateNodeInput(node, 'Surface', 'material', inputInfo)
			return inputInfo['outputInfo']['value']
		
		# Surface shader types (--> material)
		if t.startswith('BSDF_') or t in ['EMISSION', 'HOLDOUT', 'EEVEE_SPECULAR', 'SUBSURFACE_SCATTERING']:
			# trying to make a simple material from these different shaders
			# startswith('BSDF_') matches BSDF volume shaders too, however they are not supported here
			mat = {k: v['default'] for k,v in self.materialStruct.items()}
			if 'color' in mat and node.inputs.get('Base Color') is not None:
				mat['color'] = self.translateNodeInput(node, 'Base Color', self.materialStruct['color']['type'], inputInfo)
			if 'color' in mat and node.inputs.get('Color') is not None:
				mat['color'] = self.translateNodeInput(node, 'Color', self.materialStruct['color']['type'], inputInfo)
			if 'metallic' in mat and node.inputs.get('Metallic') is not None:
				mat['metallic'] = self.translateNodeInput(node, 'Metallic', self.materialStruct['metallic']['type'], inputInfo)
			if 'specular' in mat and node.inputs.get('Specular') is not None:
				mat['specular'] = self.translateNodeInput(node, 'Specular', self.materialStruct['specular']['type'], inputInfo)
			if 'roughness' in mat and node.inputs.get('Roughness') is not None:
				mat['roughness'] = self.translateNodeInput(node, 'Roughness', self.materialStruct['roughness']['type'], inputInfo)
			if 'ior' in mat and node.inputs.get('IOR') is not None:
				mat['ior'] = self.translateNodeInput(node, 'IOR', self.materialStruct['ior']['type'], inputInfo)
			if 'emission' in mat and node.inputs.get('Emission') is not None:
				mat['emission'] = self.translateNodeInput(node, 'Emission', self.materialStruct['emission']['type'], inputInfo)
			if 'emission' in mat and node.inputs.get('Emissive Color') is not None:
				mat['emission'] = self.translateNodeInput(node, 'Emissive Color', self.materialStruct['emission']['type'], inputInfo)
			if 'alpha' in mat and node.inputs.get('Alpha') is not None:
				mat['alpha'] = self.translateNodeInput(node, 'Alpha', self.materialStruct['alpha']['type'], inputInfo)
			if 'alpha' in mat and node.inputs.get('Transparency') is not None:
				mat['alpha'] = '1.0-'+self.translateNodeInput(node, 'Transparency', self.materialStruct['alpha']['type'], inputInfo)
			if 'normal' in mat and node.inputs.get('Normal') is not None:
				mat['normal'] = self.translateNodeInput(node, 'Normal', self.materialStruct['normal']['type'], inputInfo)
			if t=='HOLDOUT':
				mat = {k: v['default'] for k,v in self.materialStruct.items()}
				mat['emission'] = self.convertType('vec4(0.0,0.0,0.0,0.0)', 'vec4', self.materialStruct['emission']['type'])
				mat['color'] = self.convertType('vec4(0.0,0.0,0.0,0.0)', 'vec4', self.materialStruct['color']['type'])
				mat['alpha'] = self.convertType('0.0', 'float', self.materialStruct['alpha']['type'])
			if t=='EMISSION':
				emissionColor = self.convertType(mat['color'], self.materialStruct['color']['type'], self.materialStruct['emission']['type'])
				mat['emission'] = emissionColor+'*'+self.translateNodeInput(node, 'Strength', self.materialStruct['emission']['type'], inputInfo)
			return 'material('+(','.join([mat[k] for k in self.materialStruct]))+')'
		
		# Mix Shader and Add Shader
		if t in ['MIX_SHADER','ADD_SHADER']:
			fac = '0.5'
			if t=='MIX_SHADER':
				fac = self.translateNodeInput(node, 'Fac', 'float', inputInfo)
			shadA = self.translateNodeInput(node, ['Shader', 0], 'material', inputInfo)
			shadB = self.translateNodeInput(node, ['Shader', 1], 'material', inputInfo)
			return self.useFunction('mixMaterial', outType, [shadA,shadB,fac])
		
		# Groups (--> pass through nodes)
		if t=='GROUP':
			#output is required, find the matching input (group output) and pass through
			#check all GROUP_OUTPUT nodes and use the first one that is linked inside the group
			inputInfo['group'].append(node)
			for groupNode in node.node_tree.nodes:
				if groupNode.type == 'GROUP_OUTPUT':
					for groupNodeOutputIn in groupNode.inputs:
						if groupNodeOutputIn.name == outName:
							if groupNodeOutputIn.is_linked:
								for nodeLink in groupNodeOutputIn.links:
									n = self.translateNodeOutput(nodeLink.from_socket, inputInfo)
									return self.convertType(n['key'], n['type'], outType)
			#if none of them is linked use the default value for the output
			for groupNode in node.node_tree.nodes:
				if groupNode.type == 'GROUP_OUTPUT':
					for groupNodeOutputIn in groupNode:
						if groupNodeOutputIn.name == outName:
							n = self.translateNodeOutput(groupNodeOutputIn, inputInfo)
							return self.convertType(n['key'], n['type'], outType)
			return self.errorValue(outType, 'GROUP_OUTPUT_NOT_FOUND('+node.name+')', outputInfo)
		
		if t=='GROUP_INPUT':
			node = inputInfo['group'].pop()
			return self.translateNodeInput(node, outName, outType, inputInfo)
			
		# Mix RGB
		if t=='MIX_RGB':
			o = None
			op = node.blend_type
			outputInfo['comment'] += ' ('+op+')'
			fac = self.translateNodeInput(node, 'Fac', 'float', inputInfo)
			colA = self.translateNodeInput(node, 'Color1', 'vec4', inputInfo)
			colB = self.translateNodeInput(node, 'Color2', 'vec4', inputInfo)
			if op=='MIX':
				if clamp==True:
					return 'clamp(mix('+colA+','+colB+','+fac+'),0.0,1.0)'
				return 'mix('+colA+','+colB+','+fac+')'
			for funcName, func in self.functions.items():
				if 'enum' in func and func['enum']==op:
					if clamp==True:
						return 'clamp('+self.useFunction(funcName, outType, [colA,colB,fac])+',0.0,1.0)'
					return self.useFunction(funcName, outType, [colA,colB,fac])
			return self.errorValue(outType, 'MIX_RGB_BLEND_MODE_UNKNOWN('+op+')', outputInfo)
			
		# Bright/Contrast
		if t=='BRIGHTCONTRAST':
			color = self.translateNodeInput(node, 'Color', 'vec4', inputInfo)
			bright = self.translateNodeInput(node, 'Bright', 'float', inputInfo)
			contrast = self.translateNodeInput(node, 'Contrast', 'float', inputInfo)
			return self.useFunction('brightnessContrast', outType, [color, bright, contrast])
			
		# Gamma
		if t=='GAMMA':
			color = self.translateNodeInput(node, 'Color', 'vec4', inputInfo)
			gamma = self.translateNodeInput(node, 'Gamma', 'float', inputInfo)
			return self.useFunction('gamma', outType, [color,gamma])
		
		# Separate XYZ, Separate RGB and Separate HSV
		if t in ['SEPXYZ', 'SEPRGB']:
			return self.translateNodeInput(node, 0, 'vec3', inputInfo)+'.'+outName.lower()
		if t=='SEPHSV':
			return self.useFunction('rgb2hsv', outType, self.translateNodeInput(node, 0, 'vec3', inputInfo))+'.'+({'H':'x','S':'y','V':'z'}[outName])
			
		# Combine XYZ, Combine RGB and Combine HSV
		if t=='COMBXYZ':
			return 'vec3('+(','.join([self.translateNodeInput(node, x, 'float', inputInfo) for x in range(3)]))+')'
		if t=='COMBRGB':
			return 'vec4('+(','.join([self.translateNodeInput(node, x, 'float', inputInfo) for x in range(3)]))+',1.0)'
		if t=='COMBHSV':
			self.useFunction('hsv2rgb', outType, [self.translateNodeInput(node, x, 'float', inputInfo) for x in ['H','S','V']])
		
		# RGB to BW
		if t=='RGBTOBW':
			return self.useFunction('rgb2bw', outType, [self.translateNodeInput(node, 'Color', 'vec4', inputInfo)])
		
		# RGB
		if t=='RGB':
			return self.vecArrayType(outNode.default_value, outType)
		
		# Value
		if t=='VALUE':
			# Try to detect if this value is driven by frame
			# First check if there are drivers on the material that affect this node
			material = self.nodeTree.id_data if hasattr(self.nodeTree, 'id_data') else None
			
			# Check for frame-based drivers in multiple locations
			frame_driver_found = False
			frame_expression = None
			
			# Method 1: Check the material's animation data
			if material and hasattr(material, 'animation_data') and material.animation_data:
				for driver in material.animation_data.drivers:
					# Look for drivers that target this specific node's output
					if (node.name in driver.data_path and 
						('default_value' in driver.data_path or 'outputs' in driver.data_path)):
						expr = driver.driver.expression
						if '#frame' in expr or 'frame' in expr.lower():
							frame_expression = expr
							frame_driver_found = True
							break
			
			# Method 2: Check node tree animation data
			if not frame_driver_found and hasattr(self.nodeTree, 'animation_data') and self.nodeTree.animation_data:
				for driver in self.nodeTree.animation_data.drivers:
					if (node.name in driver.data_path and 
						('default_value' in driver.data_path or 'outputs' in driver.data_path)):
						expr = driver.driver.expression
						if '#frame' in expr or 'frame' in expr.lower():
							frame_expression = expr
							frame_driver_found = True
							break
			
			# Method 3: Check the node itself
			if not frame_driver_found and hasattr(node, 'animation_data') and node.animation_data:
				for driver in node.animation_data.drivers:
					if 'default_value' in driver.data_path or 'outputs' in driver.data_path:
						expr = driver.driver.expression
						if '#frame' in expr or 'frame' in expr.lower():
							frame_expression = expr
							frame_driver_found = True
							break
			
			# Method 4: Use Blender's driver evaluation context to detect frame usage
			if not frame_driver_found:
				try:
					import bpy
					# Check if the current value changes when we change the frame
					current_frame = bpy.context.scene.frame_current
					current_value = outNode.default_value if hasattr(outNode, 'default_value') else 0.0
					
					# Test by temporarily changing frame
					bpy.context.scene.frame_set(current_frame + 1)
					test_value = outNode.default_value if hasattr(outNode, 'default_value') else 0.0
					
					# Restore original frame
					bpy.context.scene.frame_set(current_frame)
					
					# If value changed, it's likely frame-driven
					if abs(current_value - test_value) > 0.0001:
						frame_driver_found = True
						# Create a simple frame expression
						frame_expression = 'u_frame'
				except:
					pass
			
			if frame_driver_found and frame_expression:
				# Clean up the expression to use u_frame
				frame_expr = frame_expression.replace('#frame', 'u_frame')
				frame_expr = frame_expr.replace('frame', 'u_frame')
				frame_expr = frame_expr.replace('Frame', 'u_frame') 
				frame_expr = frame_expr.replace('FRAME', 'u_frame')
				
				# Fix float literals for GLSL (e.g., 1000 -> 1000.0)
				import re
				frame_expr = re.sub(r'\b(\d+)\b', r'\1.0', frame_expr)
				
				# Handle simple cases where it's just frame * constant
				if frame_expr == 'u_frame':
					return 'u_frame'
				else:
					return f'({frame_expr})'
			
			# If no frame driver detected, return the static value
			value = outNode.default_value if hasattr(outNode, 'default_value') else 0.0
			return self.floatFormat.format(value)
		
		# Map Range
		if t=='MAP_RANGE':
			val = self.translateNodeInput(node, 'Value', 'float', inputInfo)
			fromMin = self.translateNodeInput(node, 'From Min', 'float', inputInfo)
			fromMax = self.translateNodeInput(node, 'From Max', 'float', inputInfo)
			toMin = self.translateNodeInput(node, 'To Min', 'float', inputInfo)
			toMax = self.translateNodeInput(node, 'To Max', 'float', inputInfo)
			if clamp==True:
				return self.useFunction('mapRangeClamp', outType,[val,fromMin,fromMax,toMin,toMax])
			return self.useFunction('mapRange', outType,[val,fromMin,fromMax,toMin,toMax])
		
		# Math
		if t=='MATH':
			o = None
			op = node.operation
			outputInfo['comment'] += ' ('+op+')'
			a = self.translateNodeInput(node, ['Value',0], 'float', inputInfo)
			o = 'log('+a+')' if op=='LOGARITHM' else o
			o = 'sqrt('+a+')' if op=='SQRT' else o
			o = 'abs('+a+')' if op=='ABSOLUTE' else o
			o = 'round('+a+')' if op=='ROUND' else o
			o = 'floor('+a+')' if op=='FLOOR' else o
			o = 'ceil('+a+')' if op=='CEIL' else o
			o = 'fract('+a+')' if op=='FRACT' else o
			o = 'sin('+a+')' if op=='SINE' else o
			o = 'cos('+a+')' if op=='COSINE' else o
			o = 'tan('+a+')' if op=='TANGENT' else o
			o = 'asin('+a+')' if op=='ARCSINE' else o
			o = 'acos('+a+')' if op=='ARCCOSINE' else o
			o = 'atan('+a+')' if op=='ARCTANGENT' else o
			if o is None:
				b = self.translateNodeInput(node, ['Value',1], 'float', inputInfo)
				o = '('+a+'+'+b+')' if op=='ADD' else o
				o = '('+a+'-'+b+')' if op=='SUBTRACT' else o
				o = '('+a+'*'+b+')' if op=='MULTIPLY' else o
				o = '('+a+'/'+b+')' if op=='DIVIDE' else o
				o = 'pow(abs('+a+') + 0.001, clamp('+b+', 0.1, 2.0))' if op=='POWER' else o
				o = 'min('+a+','+b+')' if op=='MINIMUM' else o
				o = 'max('+a+','+b+')' if op=='MAXIMUM' else o
				o = '(('+a+'<'+b+') ? 1.0 : 0.0)' if op=='LESS_THAN' else o
				o = '(('+a+'>'+b+') ? 1.0 : 0.0)' if op=='GREATER_THAN' else o
				o = 'mod('+a+','+b+')' if op=='MODULO' else o
				o = 'atan('+a+','+b+')' if op=='ARCTAN2' else o
			if o is None:
				return self.errorValue(outType, 'MATH_OPERATION_UNKNOWN('+op+')', outputInfo)
			if clamp==True:
				return 'clamp('+o+',0.0,1.0)'
			return o
			
		# Vector Math
		if t=='VECT_MATH':
			o = None
			op = node.operation
			outputInfo['comment'] += ' ('+op+')'
			a = self.translateNodeInput(node, ['Vector',0], 'vec3', inputInfo)
			o = 'length('+a+')' if op=='LENGTH' else o
			o = 'normalize('+a+')' if op=='NORMALIZE' else o
			o = 'floor('+a+')' if op=='FLOOR' else o
			o = 'ceil('+a+')' if op=='CEIL' else o
			o = 'fract('+a+')' if op=='FRACTION' else o
			o = 'abs('+a+')' if op=='ABSOLUTE' else o
			if op=='SCALE':
				s = self.translateNodeInput(node, 'Scale', 'float', inputInfo)
				o = '('+a+'*'+s+')' if op=='SCALE' else o
			if o is None:
				b = self.translateNodeInput(node, ['Vector',1], 'vec3', inputInfo)
				o = '('+a+'+'+b+')' if op=='ADD' else o
				o = '('+a+'-'+b+')' if op=='SUBTRACT' else o
				o = '('+a+'*'+b+')' if op=='MULTIPLY' else o
				o = '('+a+'/'+b+')' if op=='DIVIDE' else o
				o = 'cross('+a+','+b+')' if op=='CROSS_PRODUCT' else o
				o = self.useFunction('vectorProject', outType, [a,b]) if op=='PROJECT' else o
				o = 'reflect('+a+','+b+')' if op=='REFLECT' else o
				o = 'dot('+a+','+b+')' if op=='DOT_PRODUCT' else o
				o = 'distance('+a+','+b+')' if op=='DISTANCE' else o
				#o = self.useFunction('vectorSnap', outType, [a,b]) if op=='SNAP' else o # ? not implemented
				o = 'mod('+a+','+b+')' if op=='MODULO' else o
				o = 'min('+a+','+b+')' if op=='MINIMUM' else o
				o = 'max('+a+','+b+')' if op=='MAXIMUM' else o
			if o is None:
				return self.errorValue(outType, 'VECTOR_MATH_OPERATION_UNKNOWN('+op+')', outputInfo)
			return o
			
		
		# Image Texture
		if t=='TEX_IMAGE':
			if node.image is not None and node.image.name not in self.textures:
				self.textures.append(node.image.name)
			if node.image is not None:
				texId = self.textures.index(node.image.name)
				outputInfo['comment'] += ' ('+node.image.name+')'
			else:
				texId = 0
				outputInfo['comment'] += ' (no image)'
			vecSock = self.findSocket(node.inputs, 'Vector')
			samp = self.translateShaderUniform('GLSL@Textures', outputInfo)
			if vecSock is not None and vecSock.is_linked:
				vector = self.translateNodeInput(node, 'Vector', 'vec2', inputInfo)
			else:
				vector = self.translateShaderInput('TEX_COORD', 'UV', 'vec2', outputInfo)
			if outName=='Color':
				return self.convertType('texture('+samp+'['+str(texId)+'],'+vector+')', 'vec4', outType)
			elif outName=='Alpha':
				return self.convertType('texture('+samp+'['+str(texId)+'],'+vector+').a', 'float', outType)
		
		# Normal Map
		if t=='NORMAL_MAP':
			# todo: space conversion
			strength = self.translateNodeInput(node, 'Strength', 'float', inputInfo)
			color = self.translateNodeInput(node, 'Color', 'vec3', inputInfo)
			normal = self.translateShaderInput('NEW_GEOMETRY', 'Normal', 'vec3', outputInfo)
			return 'normalize('+normal+'*('+color+'*'+strength+')*0.5+0.5)'
		
		# Mapping
		if t=='MAPPING':
			if node.vector_type in ['TEXTURE','POINT']:
				loc = self.translateNodeInput(node, 'Location', 'vec3', inputInfo)
			else:
				loc = 'vec3(0.0,0.0,0.0)'
			vec = self.translateNodeInput(node, 'Vector', 'vec3', inputInfo)
			rot = self.translateNodeInput(node, 'Rotation', 'vec3', inputInfo)
			sca = self.translateNodeInput(node, 'Scale', 'vec3', inputInfo)
			return self.useFunction('mapping', outType,[vec,loc,rot,sca])
		
		# Texture Coordinate
		if t=='TEX_COORD' or t=='ShaderNodeTexCoord' or t=='TEX_COORDINATE':
			if outName=='UV':
				return self.convertType('v_texCoord', 'vec2', outType)
			elif outName=='Normal':
				return self.convertType('v_objectNormal', 'vec3', outType)
			elif outName=='Generated':
				# FIXED: Use UV coordinates for stable Generated coordinates
				# This simulates Blender's Generated coordinates in a predictable way
				return self.convertType('vec3(v_texCoord, 0.5)', 'vec3', outType)
			elif outName=='Object':
				# FIXED: Use position coordinates for Object coordinates (different from Generated)
				return self.convertType('v_position', 'vec3', outType)
			elif outName=='Camera':
				return self.convertType('v_position', 'vec3', outType)
			elif outName=='Window':
				return self.convertType('v_position.xy', 'vec2', outType)
			elif outName=='Reflection':
				return self.convertType('reflect(normalize(v_position), normalize(v_normal))', 'vec3', outType)
			else:
				return self.errorValue(outType, 'TEX_COORD_OUTPUT_UNKNOWN('+outName+')', outputInfo)
		
		# Noise Texture
		if t=='TEX_NOISE':
			# Get input parameters
			vecSock = self.findSocket(node.inputs, 'Vector')
			if vecSock is not None and vecSock.is_linked:
				vector = self.translateNodeInput(node, 'Vector', 'vec3', inputInfo)
			else:
				vector = self.translateShaderInput('TEX_COORD', 'UV', 'vec2', outputInfo)
				vector = 'vec3(' + vector + ', 0.0)'  # Convert vec2 to vec3
			
			scale = self.translateNodeInput(node, 'Scale', 'float', inputInfo)
			detail = self.translateNodeInput(node, 'Detail', 'float', inputInfo) 
			roughness = self.translateNodeInput(node, 'Roughness', 'float', inputInfo)
			
			# Check if W input is connected (4D noise)
			wSock = self.findSocket(node.inputs, 'W')
			if wSock is not None and wSock.is_linked:
				# 4D noise - get W parameter
				w_value = self.translateNodeInput(node, 'W', 'float', inputInfo)
				if outName=='Fac':
					return self.convertType(self.useFunction('noiseTexture4D', 'float', [vector, w_value, scale, detail, roughness]), 'float', outType)
				elif outName=='Color':
					noiseValue = self.useFunction('noiseTexture4D', 'float', [vector, w_value, scale, detail, roughness])
					return self.convertType('vec4(vec3(' + noiseValue + '), 1.0)', 'vec4', outType)
				else:
					return self.errorValue(outType, 'NOISE_TEXTURE_4D_OUTPUT_UNKNOWN('+outName+')', outputInfo)
			else:
				# 3D noise (original implementation)
				if outName=='Fac':
					return self.convertType(self.useFunction('noiseTexture', 'float', [vector, scale, detail, roughness]), 'float', outType)
				elif outName=='Color':
					# For color output, use the noise value for all RGB channels
					noiseValue = self.useFunction('noiseTexture', 'float', [vector, scale, detail, roughness])
					return self.convertType('vec4(vec3(' + noiseValue + '), 1.0)', 'vec4', outType)
				else:
					return self.errorValue(outType, 'NOISE_TEXTURE_OUTPUT_UNKNOWN('+outName+')', outputInfo)
		
		# Mix Node (for Blender 3.4+)
		if t=='MIX':
			# Get blend mode and data type
			blend_mode = getattr(node, 'blend_type', 'MIX')
			data_type = getattr(node, 'data_type', 'RGBA')
			
			# Get factor input - try both 'Factor' and 'Fac'
			try:
				fac = self.translateNodeInput(node, 'Factor', 'float', inputInfo)
			except:
				try:
					fac = self.translateNodeInput(node, 'Fac', 'float', inputInfo)
				except:
					fac = '0.5'  # Default factor
			
			if data_type == 'RGBA':
				# Color mixing - Blender 3.4+ uses 'A' and 'B' for color inputs
				try:
					color1 = self.translateNodeInput(node, 'A', 'vec4', inputInfo)
				except:
					try:
						color1 = self.translateNodeInput(node, 'Color1', 'vec4', inputInfo)
					except:
						color1 = 'vec4(0.0, 0.0, 0.0, 1.0)'
				
				try:
					color2 = self.translateNodeInput(node, 'B', 'vec4', inputInfo)
				except:
					try:
						color2 = self.translateNodeInput(node, 'Color2', 'vec4', inputInfo)
					except:
						color2 = 'vec4(1.0, 1.0, 1.0, 1.0)'
				
				if blend_mode == 'MIX':
					result = f'mix({color1}, {color2}, {fac})'
				elif blend_mode == 'MULTIPLY':
					result = self.useFunction('colorMixMultiply', 'vec4', [color1, color2, fac])
				elif blend_mode == 'DARKEN':
					result = self.useFunction('colorMixDarken', 'vec4', [color1, color2, fac])
				elif blend_mode == 'LIGHTEN':
					result = self.useFunction('colorMixLighten', 'vec4', [color1, color2, fac])
				elif blend_mode == 'SCREEN':
					result = self.useFunction('colorMixScreen', 'vec4', [color1, color2, fac])
				elif blend_mode == 'BURN':
					result = self.useFunction('colorMixBurn', 'vec4', [color1, color2, fac])
				elif blend_mode == 'DODGE':
					result = self.useFunction('colorMixDodge', 'vec4', [color1, color2, fac])
				else:
					# Fallback to simple mix for unsupported blend modes
					result = f'mix({color1}, {color2}, {fac})'
				
				return self.convertType(result, 'vec4', outType)
				
			elif data_type == 'FLOAT':
				# Float mixing - use 'A' and 'B' for value inputs
				try:
					value1 = self.translateNodeInput(node, 'A', 'float', inputInfo)
				except:
					try:
						value1 = self.translateNodeInput(node, 'Value1', 'float', inputInfo)
					except:
						value1 = '0.0'
				
				try:
					value2 = self.translateNodeInput(node, 'B', 'float', inputInfo)
				except:
					try:
						value2 = self.translateNodeInput(node, 'Value2', 'float', inputInfo)
					except:
						value2 = '1.0'
				
				result = f'mix({value1}, {value2}, {fac})'
				return self.convertType(result, 'float', outType)
			else:
				return self.errorValue(outType, 'MIX_DATA_TYPE_UNSUPPORTED('+data_type+')', outputInfo)
		
		# Voronoi Texture
		if t=='TEX_VORONOI':
			# Get input parameters
			vecSock = self.findSocket(node.inputs, 'Vector')
			if vecSock is not None and vecSock.is_linked:
				vector = self.translateNodeInput(node, 'Vector', 'vec3', inputInfo)
			else:
				vector = self.translateShaderInput('TEX_COORD', 'UV', 'vec2', outputInfo)
				vector = 'vec3(' + vector + ', 0.0)'  # Convert vec2 to vec3
			
			scale = self.translateNodeInput(node, 'Scale', 'float', inputInfo)
			smoothness = self.translateNodeInput(node, 'Smoothness', 'float', inputInfo)
			
			# Exponent might not exist in all Voronoi versions
			try:
				exponent = self.translateNodeInput(node, 'Exponent', 'float', inputInfo)
			except:
				exponent = '0.5'  # Default exponent
				
			randomness = self.translateNodeInput(node, 'Randomness', 'float', inputInfo)
			
			# Get feature type
			feature = getattr(node, 'feature', 'F1')
			distance = getattr(node, 'distance', 'EUCLIDEAN')
			
			if outName == 'Distance':
				return self.convertType(self.useFunction('voronoiTexture', 'float', [vector, scale, smoothness, exponent, randomness]), 'float', outType)
			elif outName == 'Color':
				voronoiValue = self.useFunction('voronoiTexture', 'float', [vector, scale, smoothness, exponent, randomness])
				return self.convertType('vec4(vec3(' + voronoiValue + '), 1.0)', 'vec4', outType)
			elif outName == 'Position':
				return self.convertType('vec3(0.0)', 'vec3', outType)  # Simplified
			elif outName == 'W':
				return self.convertType('0.0', 'float', outType)  # Simplified
			elif outName == 'Radius':
				return self.convertType('0.0', 'float', outType)  # Simplified
			else:
				return self.errorValue(outType, 'VORONOI_OUTPUT_UNKNOWN('+outName+')', outputInfo)
		
		# Vector Rotate Node
		if t=='VECTOR_ROTATE':
			# Get input parameters
			vector = self.translateNodeInput(node, 'Vector', 'vec3', inputInfo)
			center = self.translateNodeInput(node, 'Center', 'vec3', inputInfo)
			axis = self.translateNodeInput(node, 'Axis', 'vec3', inputInfo)
			angle = self.translateNodeInput(node, 'Angle', 'float', inputInfo)
			
			# For simplicity, we'll implement basic rotation around Z-axis
			# More complex rotation would require proper rotation matrices
			if outName == 'Vector':
				# Simple 2D rotation in XY plane (ignoring complex 3D rotation for now)
				result = f'vec3(({vector}.x - {center}.x) * cos({angle}) - ({vector}.y - {center}.y) * sin({angle}) + {center}.x, ({vector}.x - {center}.x) * sin({angle}) + ({vector}.y - {center}.y) * cos({angle}) + {center}.y, {vector}.z)'
				return self.convertType(result, 'vec3', outType)
			else:
				return self.errorValue(outType, 'VECTOR_ROTATE_OUTPUT_UNKNOWN('+outName+')', outputInfo)
		
		# Reroute Node (pass-through)
		if t=='REROUTE':
			# Reroute just passes the input through unchanged
			input_socket = self.findSocket(node.inputs, 'Input')
			if input_socket is not None and input_socket.is_linked:
				return self.translateNodeInput(node, 'Input', outType, inputInfo)
			else:
				return self.errorValue(outType, 'REROUTE_INPUT_NOT_CONNECTED', outputInfo)
		
		# Unsupported Nodes
		return self.errorValue(outType, 'NODE_TYPE_UNKNOWN('+node.type+')', outputInfo)
		
	def translateShaderOutput(self, keyName):
		for k,v in self.outputs.items():
			if v['key']==keyName:
				return k
		return self.errorValue('string', 'SHADER_OUTPUT_NOT_FOUND('+keyName+')')
		
	def translateShaderUniform(self, keyName, outputInfo=None):
		for k,v in self.uniforms.items():
			if v['key']==keyName:
				return k
		return self.errorValue('string', 'SHADER_UNIFORM_NOT_FOUND('+keyName+')')
	
	def translateShaderInput(self, nodeName, socketName, expectType, outputInfo=None):
		name = nodeName+'@'+socketName
		for k,v in self.inputs.items():
			if 'nodes' in v:
				if type(v['nodes']) is str:
					if name==v['nodes']:
						return self.convertType(k, v['type'], expectType)
				elif type(v['nodes']) is list:
					for n in v['nodes']:
						if name==n:
							return self.convertType(k, v['type'], expectType)
		return self.errorValue(expectType, 'SHADER_INPUT_NOT_FOUND('+name+')', outputInfo)
		
	def translateNodeOutput(self, nodeOutput, fromInput):
		lastOutput = fromInput['outputInfo']
		outputId = '['+('->'.join([('main' if x==None else x.name) for x in fromInput['group']]))+']->'+nodeOutput.node.name+'~'+nodeOutput.identifier
		for var in self.vars:
			if var['outputId']==outputId:
				var['required'].append(lastOutput)
				return var
		varId = len(self.vars)
		var = {'group':fromInput['group'], 'outputId':outputId, 'id':varId, 'key':self.varPrefix+str(varId), 'required':[lastOutput]}
		var['type'] = {'SHADER':'material', 'VALUE':'float', 'RGBA':'vec4', 'VECTOR':'vec3'}[nodeOutput.type]
		var['node'] = nodeOutput.node
		var['nodeOutput'] = nodeOutput
		var['comment'] = nodeOutput.node.bl_label+' -> '+nodeOutput.node.type+'@'+nodeOutput.name
		self.vars.append(var)
		var['error'] = False
		var['value'] = self.translateNode(nodeOutput.node, var)
		return var
	
	def translateNodeInput(self, node, inputName, expectType, inputInfo):
		lastOutput = inputInfo['outputInfo']
		nodeInput = self.findSocket(node.inputs, inputName)
		if nodeInput is None:
			return self.errorValue(expectType, 'INPUT_NOT_FOUND('+str(inputName)+' for '+node.name+')', lastOutput)
		if nodeInput.is_linked:
			for link in nodeInput.links:
				e = self.translateNodeOutput(link.from_socket, inputInfo)
				return self.convertType(e['key'], e['type'], expectType)
		elif expectType=='material':
			return self.materialDefault
		elif nodeInput.type=='SHADER':
			return self.convertType(self.materialDefault, 'material', expectType)
		elif nodeInput.type=='VALUE':
			return self.convertType(self.floatFormat.format(nodeInput.default_value), 'float', expectType)
		elif nodeInput.type=='RGBA':
			return self.convertType('vec4('+(','.join([self.floatFormat.format(x) for x in nodeInput.default_value]))+')', 'vec4', expectType)
		elif nodeInput.type=='VECTOR':
			return self.convertType('vec3('+(','.join([self.floatFormat.format(x) for x in nodeInput.default_value]))+')', 'vec3', expectType)
		return self.errorValue(expectType, 'INPUT_UNKNOWN('+nodeInput.name+')', lastOutput)
	
	def vecArrayType(self, vecArray, outType):
		t = 'vec'+str(len(vecArray))
		return self.convertType(t+'('+(','.join([self.floatFormat.format(x) for x in vecArray]))+')', t, outType)
	
	def convertType(self, value, inType, outType):
		if inType==outType:
			return value
		if inType=='float':
			if outType=='vec2':
				return 'vec2('+value+')'
			elif outType=='vec3':
				return 'vec3('+value+')'
			elif outType=='vec4':
				return 'vec4(vec3('+value+'),1.0)'
			elif outType=='material':
				# Convert float to material with default values, using float as base color intensity
				return 'material(vec4(vec3('+value+'),1.0),0.0,vec4(0.5,0.5,0.5,1.0),0.5,1.45,vec4(0.0,0.0,0.0,1.0),1.0,vec3(0.0,0.0,0.0))'
		if inType=='vec2':
			if outType=='float':
				return value+'.x'
			if outType=='vec3':
				return 'vec3('+value+',0.0)'
			if outType=='vec4':
				return 'vec4('+value+',0.0,1.0)'
		if inType=='vec3':
			if outType=='float':
				return value+'.r'
			if outType=='vec2':
				return value+'.xy'
			if outType=='vec4':
				return 'vec4('+value+',1.0)'
			elif outType=='material':
				# Convert vec3 to material using it as base color
				return 'material(vec4('+value+',1.0),0.0,vec4(0.5,0.5,0.5,1.0),0.5,1.45,vec4(0.0,0.0,0.0,1.0),1.0,vec3(0.0,0.0,0.0))'
		if inType=='vec4':
			if outType=='float':
				return value+'.x'
			if outType=='vec2':
				return value+'.xy'
			if outType=='vec3':
				return value+'.xyz'
			elif outType=='material':
				# Convert vec4 to material using it as base color
				return 'material('+value+',0.0,vec4(0.5,0.5,0.5,1.0),0.5,1.45,vec4(0.0,0.0,0.0,1.0),'+value+'.a,vec3(0.0,0.0,0.0))'
		if inType=='material':
			if outType=='vec4':
				return value+'.color'
			elif outType=='vec3':
				return value+'.color.xyz'
			elif outType=='float':
				return value+'.color.x'
		return self.errorValue(outType, 'CONVERSION_UNKNOWN('+inType+' -> '+outType+' for '+value+')')
	
	def findSocket(self, sockets, name):
		if type(name)==str:
			return sockets.get(name)
		if type(name)==list and len(name)>=2:
			num = name[1]
			for n in sockets:
				if n.name == name[0]:
					if num==0:
						return n
					num -= 1
		if type(name)==int:
			return sockets[name]
		return None
		
	def useFunction(self, funcName, returnType=None, params=None):
		if not funcName in self.functions:
			return self.errorValue(returnType, 'FUNCTION_NOT_DEFINED('+funcName+')')
		f = self.functions[funcName]
		add = True
		for func in self.useFunctions:
			if func['name']==funcName:
				add = False
				break
		if add==True:
			for r in self.functions[funcName]['require']:
				self.useFunction(r)
			self.useFunctions.append(f)
		if params is None:
			params = []
		if returnType==None:
			return None
		return self.convertType(funcName+'('+(','.join(params))+')', f['returnType'], returnType)
	
	def virtualVar(self, varType, varKey, varId, varValue):
		return {'key':varKey, 'type':varType, 'uses':0, 'id':varId, 'required':[], 'outputId':'main', 'comment':'compiled output', 'error':False, 'value':varValue}
		
	def errorValue(self, valueType, error, outputInfo=None):
		self.errors.append(error)
		if outputInfo!=None:
			outputInfo['error'] = True
		if self.forceValidTranslation:
			if valueType=='float':
				return '0.0 /* '+error+' */ '
			if valueType=='vec2':
				return 'vec2(0.0,0.0) /* '+error+' */ '
			if valueType=='vec3':
				return 'vec3(0.0,0.0,0.0) /* '+error+' */ '
			if valueType=='vec4':
				return 'vec4(0.0,0.0,0.0,1.0) /* '+error+' */ '
			if valueType=='material':
				return self.materialDefault+' /* '+error+' */ '
		return error
