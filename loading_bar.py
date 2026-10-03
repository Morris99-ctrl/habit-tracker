
import time
import os

num_steps = 6
bar = []

for i in range(1,num_steps + 1):
    bar.append("🍽️")
    percent = int((i / num_steps) * 100)

    os.system("cls" if os.name == "nt" else "clear")
    print(f"Loading: {percent}% {" ".join(bar)}")
    time.sleep(0.3)
    bar[-1] = "🍗"


    os.system("cls" if os.name == "nt" else "clear")
    print(f"Loading: {percent}% {" ".join(bar)}")
    time.sleep(0.3)

    bar[-1] = "🍽️"

