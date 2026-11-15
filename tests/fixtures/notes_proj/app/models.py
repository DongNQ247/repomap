class User:
    def __init__(self, name):
        self.name = name

    def display(self):
        return self.name.title()


def make_user(name):
    return User(name)
