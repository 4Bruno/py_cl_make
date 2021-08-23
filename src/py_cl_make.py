# Everything is a .dll
# * .lib is a .dll with more information so you can link statically
#
# * .exe is a .dll with a function called "main" which is the function which OS will call
#	to start running the program
#
# * .dll is binary file with hardware specific cpu instructions
# !!!!!!!!!!! IMPORTANT !!!!!!!!!!!
# To compiler the difference between dll and lib is whether you explicitly
# export functions using __declspec( dllexport) before the function definition
# or passing to the linker the list of functions that must be exported
# For the compiler is the hint for "Oh, so you want to link statically this func"
# !!!!!!!!!!! IMPORTANT !!!!!!!!!!!
# Usage:
# Requires running visual studio script to set environment variables before running this
# default path like:
# C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat
import sys 
import os
import subprocess as sp
from contextlib import contextmanager
import datetime

@contextmanager
def cwd(path):
	oldpwd=os.getcwd()
	if not os.path.exists(path): os.mkdir(path)
	os.chdir(path)
	try:
		yield
	finally:
		os.chdir(oldpwd)

"""
In simple C nested struct like (vector 2 implementation):
struct v2
{
    union
    {
        float Array[2];
        struct
        {
            float x;
            float y;
        };
    };
};
"""
DISABLE_WARNING_NAMELESS_STRUCT = '/wd4201'
DISABLE_WARNING_VAR_INITIALIZED_NOTUSED = '/wd4189'
DISABLE_WARNING_UNREFERENCED_FORMAL_PARAM = '/wd4100'
DEFAULT_WARNINGS = ('/W4',
					DISABLE_WARNING_NAMELESS_STRUCT,
					DISABLE_WARNING_VAR_INITIALIZED_NOTUSED,
					DISABLE_WARNING_UNREFERENCED_FORMAL_PARAM
					)

class Compiler:
	def __init__(self):
		self.last_modified = {}
		with open('.compiler_cache.db','a+') as db:
			db.seek(0)
			for line in db.readlines():
				if (len(line) > 0):
					source_file, timestamp = line.split(',')
					self.last_modified[source_file] = \
						datetime.datetime.strptime(timestamp.replace('\n',''),'%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
		vcvars64Invoked = True

	def __enter__(self):
		return self

	def __exit__(self,*exc_details):
		with open('./.compiler_cache.db','w+') as db:
			for dll in self.last_modified:
				entry = ','.join([dll,datetime.datetime.fromtimestamp(os.path.getmtime(dll)).strftime('%Y-%m-%d %H:%M:%S')])
				db.write(entry + '\n')
			db.flush()

	def __BuildDll(self,is_exe,dlls,ext_libs, debug_mode):
		need_compilation = False
		for dll in dlls:
			if dll in self.last_modified:
				last_time_stamp = self.last_modified[dll]
				new_time_stamp = datetime.datetime.fromtimestamp(os.path.getmtime(dll)).strftime('%Y-%m-%d %H:%M:%S')
				if last_time_stamp != new_time_stamp:
					need_compilation = True
					break
			else:
				need_compilation = True
				break
		if not need_compilation:
			print("No changes. Skipping compilation for %s" % (dlls[0]))
			return
		PopenListArgs = ['cl','/nologo']
		WarningArgs = DEFAULT_WARNINGS
		Optimization = '/Od' if debug_mode else '/O2'
		CompilerArgs = ['/MTd','/Zi','/I..\..\include',Optimization]
		if not is_exe: CompilerArgs.insert(0,'/LD')
		LinkerArgs = ['/link','/incremental:no','/opt:ref']
		if not is_exe: LinkerArgs.insert(1,'/DLL')
		PopenListArgs.extend(CompilerArgs)
		PopenListArgs.extend(WarningArgs)
		PopenListArgs.extend(dlls)
		PopenListArgs.extend(LinkerArgs)
		PopenListArgs.extend(ext_libs)
		self.__Compile(PopenListArgs,dlls)

	def BuildLib(self,dlls,ext_libs, debug_mode):
		self.__BuildDll(False,dlls,ext_libs,debug_mode)

	def BuildExe(self,dlls,ext_libs, debug_mode):
		self.__BuildDll(True,dlls,ext_libs,debug_mode)

	def __Compile(self, Args, dlls):
		Compilation = sp.Popen(Args)
		output, errors = Compilation.communicate()
		Compilation.wait()
		if output: print("Output: %s" % output)
		if errors: print("Errors: %s" % errors)
		if errors is None:
			for dll in dlls:
				self.last_modified[dll] = os.path.getmtime(dll)
		print('\n'.join(dlls))


class Dll:
	def __init__(self, source_files, external_libs=[]):
		self.source_files = []
		self.external_libs = []
		for file in source_files:
			self.add_source_file(file)
		for lib in external_libs:
			self.add_external_lib(lib)

	def add_source_file(self, file):
		assert(file.endswith('.cpp') or file.endswith('.c'))
		self.source_files.append(file)
	def add_external_lib(self, lib):
		assert(lib.endswith('.lib'))
		self.external_libs.append(lib)

def BuildSolution(dlls,debug_mode=False):
	print("Building %s solution" % ("'Debug mode'" if debug_mode else "'Release mode'"))
	build_path = 'debug' if debug_mode else 'release'
	script_path = os.path.dirname(os.path.abspath(__file__))
	code_path = os.path.join(script_path,'src')
	if os.path.exists(code_path):
		output_folder = os.path.join(code_path,build_path) + '\\'
		with cwd(output_folder):
			with Compiler() as compiler:
				for dll in dlls:
					compiler.BuildLib(dll.source_files,dll.external_libs, debug_mode=debug_mode)

"""
Add here custom builds
Folder structure expected:
    py_cl_make.py
    include/
    src/
        main.cpp
        other.cpp
        debug/
        release/
"""

SomeLib = Dll(['../my_lib.cpp'])
SomeExe = Dll(['../main.cpp'],['kernel32.lib','User32.lib','winmm.lib','my_lib.lib'])

#!!!! No dependency check. Order of elements defines dependency
DLLS_SOLUTION = [
		SomeLib,
        SomeExe	
	]

if __name__ == '__main__':
	debug_mode = False
	if len(sys.argv) > 1:
		if '/D' in sys.argv:
			debug_mode = True
        else:
            print("Flag not supported. Only expected /D for debug build")
	BuildSolution(DLLS_SOLUTION,debug_mode)

