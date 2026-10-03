#Guess the number

import random
secret = random.randint(0, 9)

while True:
    guess = int(input("\nEnter your guess: "))
    if guess == secret:
        print("Correct! You did it!")
        break

    else:
        print("Oh Noo! Try Again")
