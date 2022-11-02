# A script to generate a 1024kb file with random data
with open("small.txt", "a") as f:
    for i in range(1024):
        f.write("a")
    f.close()