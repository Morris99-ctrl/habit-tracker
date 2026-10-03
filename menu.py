# Hotel Menu.

print("Welcome to Veliq Hotel.. \n" \
      "A hotel known for it's services and have a 4.8⭐ rating!🥰")

print("What would you like to have? Take a look at our menu.\n")

# Store menu items in a dictionary.

menu = {
    "1": "Smashed Potatoes with sauce",
    "2": "Fried Chicken",
    "3": "Grilled Salmon",
    "4": "Ceasar Salad",
    "5": "Shawarma",
    "6": "Lobsters",
    "7": "Margherita",
    "8": "Grilled Cheese",
    "9": "Spaghetti Bolognese",
    "10": "Burritos"
}

# Display the menu

for number, food in menu.items():
    print(f"{number}. {food}")

while True:
    choice = input("\nPlease enter the number of your choice: ")
    #Check if choice exists in menu
    if choice in menu:
        selected_food = menu[choice]
        print(f"\nYou have selected {selected_food}. Please wait as we get your order ready!")
    else:
        print("\nYou have entered an invalid input 😌. Please try again!")
        continue  # ask again for choice

    # Ask if they want something else
    more = input("\nWould you like to order something else? (yes/no): ").strip().lower()
    if more != 'yes':
        print("\nThank you for your order! Have a great day!")
        break

