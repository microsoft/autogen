import os

for var in os.environ:
    print(var + ": " + os.environ[var])
