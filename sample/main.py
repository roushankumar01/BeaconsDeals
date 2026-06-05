import sys
from animals import Dog, Cat
from shelter import Shelter

def main():
    my_shelter = Shelter()

    buddy = Dog("Buddy")
    whiskers = Cat("Whiskers")

    my_shelter.add_animal(buddy)
    my_shelter.add_animal(whiskers)

    print("Welcome to the animal shelter!")
    my_shelter.roll_call()

if __name__ == "__main__":
    main()
