import os
import py_compile

# If the script is run, it will compile all files in its directory except itself
if __name__ == "__main__":
    # List all files in directory
    directory = os.listdir(os.path.dirname(os.path.realpath(__file__)))
    # Delete old *.pyc files
    for file in directory:
        if file.endswith(".pyc"):
            os.remove(file)
    for file in directory:
        # Compile *.py files, omit setup.py
        if file.endswith(".py") and not file.startswith("setup.py"):
            fname = file.__str__()
            cname = fname+"c"
            print("Compiling", fname, "to", cname)
            # Compile file
            py_compile.compile(fname, cname)
