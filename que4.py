age = int(input("Enter age: "))
citizen = input("Are you an Indian citizen? (yes/no): ")

if age >= 18 and citizen == "yes":
    print("Eligible for voting")
    if age>=110:
     print("Not Human")
else:
    print("Not eligible for voting")