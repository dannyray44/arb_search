import json

from betting_event import Bookmaker


class UserBookmaker(Bookmaker):
    DEFAULTS = json.load(open("settings/event_defaults.json", "r"))["bookmaker"]

    def __init__(self,
                 name: str,
                 commission: float = DEFAULTS['commission'],
                 balance: float = DEFAULTS['balance'], 
                 percent_of_balance: float = DEFAULTS['percent_of_balance'],
                 ignore_wager_precision: bool = DEFAULTS['ignore_wager_precision'],
                 max_wager_count: int = DEFAULTS['max_wager_count']
                ) -> None:

        super().__init__(commission, wager_limit=balance*percent_of_balance, ignore_wager_precision= ignore_wager_precision, max_wager_count= max_wager_count)

        self.name = name
        self.balance = balance
        self.percent_of_balance = percent_of_balance

    @classmethod
    def from_dict(cls, name: str, __bookmaker_dict: dict) -> 'UserBookmaker':
        if "balance" not in __bookmaker_dict and "percent_of_balance" not in __bookmaker_dict:
            return super().from_dict(__bookmaker_dict)
        if "name" in __bookmaker_dict:
            result = cls(**__bookmaker_dict)
        else:
            result = cls(name= name, **__bookmaker_dict)
        if "id" in __bookmaker_dict:
            result._id = __bookmaker_dict["id"]
        return result

    def as_dict(self, verbose: bool = False) -> dict:
        if verbose:
            return {
                "name": self.name,
                "commission": self.commission,
                "balance": self.balance,
                "percent_of_balance": self.percent_of_balance,
                "ignore_wager_precision": self.ignore_wager_precision,
                "max_wager_count": self.max_wager_count
            }
        else:
            return super().as_dict()

    
    def __eq__(self, __value: object) -> bool:
        if hasattr(__value, "name"):
            return self.name == getattr(__value, "name")
        return super().__eq__(__value)
