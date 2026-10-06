from .storage import load_json
from .storage import save_json


class Memory:

    def __init__(self):

        self.path = "data/memory.json"

        self.memories = load_json(
            self.path,
            []
        )

    def add(self, text):

        if text not in self.memories:

            self.memories.append(text)

            save_json(
                self.path,
                self.memories
            )

    def get_all(self):

        return self.memories

    def exists(self, text):

        return text in self.memories

    def remove(self, keyword):

        remaining = [m for m in self.memories if keyword not in m]
        removed = len(self.memories) - len(remaining)
        if remaining != self.memories:
            self.memories = remaining
            save_json(self.path, self.memories)
        return removed