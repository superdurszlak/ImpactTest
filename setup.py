import os
import py_compile
if __name__ == "__main__":
    directory = os.listdir(os.path.dirname(os.path.realpath(__file__)))
    for file in directory:
        if file.endswith(".pyc"):
            os.remove(file)
    for file in directory:
        if file.endswith(".py") and not file.startswith("setup"):
            fname = file.__str__()
            cname = fname+"c"
            print("Compiling", fname, "to", cname)
            py_compile.compile(fname, cname)