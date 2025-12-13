import random

# Generate 1,000 random numbers between 0 and 100,000
numbers = [random.randint(0, 100000) for _ in range(1000)]

# Write numbers to test.txt, one per line
with open("demo-audio-data.csv", "w") as f:
    for number in numbers:
        f.write(f"{number}\n")
