class Guard:
    def __init__(self, name):
        self.name = name
        self.armor = 100

    def __str__(self):
        return f"{self.name} has {self.armor} armor"

    def take_damage(self, damage):
        self.armor -= damage

    def get_armor(self):
        return self.armor

    def is_alive(self):
        return self.armor > 0
