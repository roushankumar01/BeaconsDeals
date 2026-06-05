from .animals import Dog, Cat

class Shelter:
    def __init__(self):
        self.animals = []

    def add_animal(self, animal):
        self.animals.append(animal)

    def roll_call(self):
        for animal in self.animals:
            print(animal.speak())
