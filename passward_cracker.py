import random
import time 

password = input("\nEnter your password: ")

print("\n🔐 Hacking Password....")
time.sleep(1)

chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@%&?*+="

for i in range(len(password)):
    while True:
        guess = "".join(
            random.choice(chars) for _ in range(i + 1)
        )

        print("\n🔐" + guess, end="")
        time.sleep(0.03)

        if random.randint(1, 15) == 1:
            break


print("\nPASSWORD FOUND:", password)

