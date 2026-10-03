#python Calculator
#Its A Simple Calculator using the if, else and eilf functions..

operator = input("\nEnter an operator ( +, -, /, *): ")
num1 = float(input("\nEnter the first Number: "))
num2 = float(input("\nEnter the second Number: "))

if operator == "+":
    result = num1 + num2
    print(round(result, 3))

elif operator == "-":
    result = num1 - num2
    print(round(result, 3))

elif operator == "*":
    result = num1 * num2
    print(round(result, 3))

elif operator == "/":
     if num2 == 0:
            print("Error!! Cannot divide by Zero!")

     elif num2 != 0:

        result = num1 / num2
        print(round(result, 3))

        
else:
    print(f"{operator} is not a valid operator! Please Try Again!!")

print("Success!")

