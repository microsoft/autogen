
# This script increments the integer contained by ./index.txt by 1.

with open("./index.txt", "r") as file:
    index = int(file.read().strip())
index += 1
with open("./index.txt", "w") as file:
    file.write(str(index))
print(index)
