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
    def __init__(self,relative_src_files):
        self.last_modified = {}
        self.system_files_cache = {}
        self.dirty_dll = [] 
        self.relative_src_files = relative_src_files
        system_paths = os.environ["PATH"].split(";")
        system_paths.append(os.getcwd())
        for d in system_paths:
            if os.path.exists(d):
                for f in os.listdir(d):
                    self.system_files_cache[f.lower()] = os.path.join(d,f)
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
                entry = ','.join([dll,self.last_modified[dll]])
                db.write(entry + '\n')
            db.flush()

    def getFileTimeStamp(self,file):
        # check cwd
        file = file.lower()
        if not os.path.exists(file):
            if not file in self.system_files_cache:
                if file.endswith('.lib'):
                    file = file.replace('.lib','.dll')
                if not file in self.system_files_cache:
                    raise Exception("File (%s) can't be found in project or system files" % (file))
            file = self.system_files_cache[file]
        return datetime.datetime.fromtimestamp(os.path.getmtime(file)).strftime('%Y-%m-%d %H:%M:%S')

    def __BuildDll(self,is_exe,dlls,ext_libs, debug_mode, use_cache):
        name = dlls[0].replace('.lib','.dll')
        dlls_fullpath = []
        for dll in dlls:
            dlls_fullpath.append(os.path.join(self.relative_src_files, dll))
        need_compilation = (name in self.dirty_dll)
        if use_cache and not need_compilation:
            for dll in dlls_fullpath:
                if dll in self.last_modified:
                    last_time_stamp = self.last_modified[dll]
                    new_time_stamp = self.getFileTimeStamp(dll)
                    if last_time_stamp != new_time_stamp:
                        need_compilation = True
                        break
                else:
                    need_compilation = True
                    break
            for lib in ext_libs:
                if lib in self.last_modified:
                    last_time_stamp = self.last_modified[lib]
                    new_time_stamp = self.getFileTimeStamp(lib)
                    if last_time_stamp != new_time_stamp:
                        print("lib %s changed" % lib)
                        need_compilation = True
                        break
                    else:
                        print("lib %s didnt changed" % lib)

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
        PopenListArgs.extend(dlls_fullpath)
        PopenListArgs.extend(LinkerArgs)
        PopenListArgs.extend(ext_libs)
        self.__Compile(name,PopenListArgs,dlls_fullpath,ext_libs)

    def BuildLib(self,dlls,ext_libs, debug_mode,use_cache):
        self.__BuildDll(False,dlls,ext_libs,debug_mode,use_cache)

    def BuildExe(self,dlls,ext_libs, debug_mode,use_cache):
        self.__BuildDll(True,dlls,ext_libs,debug_mode,use_cache)

    def __Compile(self, name, Args, dlls, ext_libs):
        try:
            Compilation = sp.Popen(Args)
            output, errors = Compilation.communicate()
            Compilation.wait()
            if output: print("Output: %s" % output)
            if errors: print("Errors: %s" % errors)
            if errors is None:
                for dll in dlls:
                    self.last_modified[dll] = self.getFileTimeStamp(dll)
                for lib in ext_libs:
                    self.last_modified[lib] = self.getFileTimeStamp(lib)
                if not name in self.dirty_dll:
                    self.dirty_dll.append(name)
        except Exception as e:
            raise Exception("Error compiling %s" % name)



class Dll:
    def __init__(self, source_files, external_libs=[],executable=False):
        self.source_files = []
        self.external_libs = []
        self.executable = executable
        for file in source_files:
            self.add_source_file(file)
        for lib in external_libs:
            self.add_external_lib(lib)

    def add_source_file(self, file):
        assert(file.endswith('.cpp') or file.endswith('.c') or file.endswith('.lib') or file.endswith('.obj'))
        self.source_files.append(file)
    def add_external_lib(self, lib):
        assert(lib.endswith('.lib') or lib.endswith('.obj'))
        self.external_libs.append(lib)

def BuildSolution(dlls,relative_src_files,debug_mode=False,use_cache=True):
    print("Building %s solution" % ("'Debug mode'" if debug_mode else "'Release mode'"))
    build_path = 'debug' if debug_mode else 'release'
    script_path = os.path.dirname(os.path.abspath(__file__))
    code_path = os.path.join(script_path,relative_src_files)
    output_folder = os.path.join(code_path,build_path) + '\\'
    if not use_cache:
        known_build_files_ext = ['.lib','.obj','.pdb','.dll','.exe']
        for file in os.listdir(output_folder):
            file_ext = None
            try:
                file_ext = file[file.rindex('.'):]
            except:
                pass
            if file_ext in known_build_files_ext:
                os.remove(os.path.join(output_folder,file))
    if os.path.exists(code_path):
        with cwd(output_folder):
            relative_src_files = os.path.join(script_path,relative_src_files)
            with Compiler(relative_src_files) as compiler:
                for dll in dlls:
                    if dll.executable:
                        compiler.BuildExe(dll.source_files,dll.external_libs, debug_mode=debug_mode,use_cache=use_cache)
                    else:
                        compiler.BuildLib(dll.source_files,dll.external_libs, debug_mode=debug_mode,use_cache=use_cache)

"""
Folder structure expected:
    py_cl_make.py
    include/
    src/
        main.cpp
        test.cpp
        debug/
        release/
"""

Test = Dll(['test.cpp'])
Exe = Dll(['main.cpp'],['test.obj'],executable=True)


DLLS_SOLUTION = [Test, Exe]


if __name__ == '__main__':
    debug_mode = False
    use_cache = True
    relative_src_files = 'src'
    #use_cache = False
    if len(sys.argv) > 1:
        if '/D' in sys.argv:
            debug_mode = True
        if '/F' in sys.argv:
            use_cache = False
    BuildSolution(DLLS_SOLUTION,relative_src_files,debug_mode=debug_mode,use_cache=use_cache)

