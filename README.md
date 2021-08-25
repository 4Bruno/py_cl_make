Simple python script to create dlls using cl.exe (Visual studio)

It requires running vcvars64.bat (visual studio script to setup environ variables)
before running python script (as it expects all the system paths where .exe can be found)

The build system is intended to be hardcoded in the script itself.

All the compiler flags are custom for the projects I work with.

It has minimal "last modified" check to avoid compiling dlls without changes.

Folder structure:
py_cl_make.py
src\
    main.cpp
    test.cpp
    debug\
    release\

In script setup your build as follows:

```
Test = Dll(['test.cpp'])
Main = Dll(['main.cpp'],['test.obj'],executable=True)

# global list with all dlls to create
DLLS_SOLUTION = [Test, Exe]
```

Flags:
/D Debug build (will set optimizations and full debugging exports)
/F Force build. Do not use cache
