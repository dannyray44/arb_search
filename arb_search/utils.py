import os
import json

import pickle
from typing import Dict, Literal, Optional, List

from arb_search.user_event.bookmaker import UserBookmaker

from difflib import SequenceMatcher

class StoredDict(dict):
    def __init__(self, filename, method: Literal["pickle", "json"] = "pickle", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = filename
        if method not in ["pickle", "json"]:
            raise ValueError(f"Invalid format {format}")
        self.method = method
        self.load()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.save()

    def __delitem__(self, key):
        super().__delitem__(key)
        self.save()

    def clear(self):
        super().clear()
        self.save()

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self.save()

    def load(self):
        try:
            if self.method == "pickle":
                with open(self.filename, 'rb') as f:
                    self.update(pickle.load(f))
            elif self.method == "json":
                with open(self.filename, 'r') as f:
                    self.update(json.load(f))
        except EOFError:
            self.update({})
        except FileNotFoundError:
            if os.path.dirname(self.filename): # if self.filename has a path, create the directory 
                os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            self.update({})

    def save(self):
        if self.method == "pickle":
            with open(self.filename, 'wb') as f:
                pickle.dump(dict(self), f)
        elif self.method == "json":
            with open(self.filename, 'w') as f:
                json.dump(dict(self), f, indent=4)


class BookmakerStoredDict(Dict[str, UserBookmaker]):
    def __init__(self, bookmaker_stored_dict: Optional[StoredDict] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if bookmaker_stored_dict is None:
            bookmaker_stored_dict = StoredDict('settings/bookmakers.json', method= 'json')
        self.__dict_representation = bookmaker_stored_dict
        # bookmaker_stored_dict.load()
        self._update_from_stored_dict()

    def _update_from_stored_dict(self):
        for key, value in self.__dict_representation.items():
            if key in self:
                value["id"] = self[key]._id
            self[key] = UserBookmaker.from_dict(key, value)

    def _update_stored_dict(self):
        for key, value in self.items():
            self.__dict_representation[key] = value.as_dict(verbose= True)

    def load(self):
        self.__dict_representation.load()
        self._update_from_stored_dict()

    def save(self):
        self._update_stored_dict()
        self.__dict_representation.save()


def team_name_matcher(name:str, team_names: List[str]) -> str:
    """Finds the closest match to name in team_names."""
    return max(team_names, key= lambda x: SequenceMatcher(None, name.lower(), x.lower()).ratio())