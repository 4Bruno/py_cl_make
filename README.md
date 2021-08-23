Simple python script to create dlls using cl.exe (Visual studio)

It requires running vcvars64.bat (visual studio script to setup environ variables)
before running python script (as it expects all the system paths where .exe can be found)

The built system is intended to be hardcoded in the script itself.

All the compiler flags are custom for the projects I work with.

It has minimal "last modified" check to avoid compiling dlls without changes.


