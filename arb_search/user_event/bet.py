import json
from datetime import datetime
from typing import Any, Dict, Optional, Type, Union

# from arb_search.apis.base_api import API_Instance
from betting_event import Bet, BetType

from .bookmaker import UserBookmaker


class UserBet(Bet):
    DefaultBookmaker = UserBookmaker("Default Bookmaker")
    Defaults = json.load(open("settings/event_defaults.json", "r"))["bet"]

    def __init__(self, bet_type: Union[BetType, str, int], value: str, odds: float,
                 bookmaker: Optional[UserBookmaker] = None, lay: bool = False, volume: float = -1.0,
                 previous_wager: float = Defaults["previous_wager"], wager: float = 0.0,
                 update_time: Optional[datetime] = None, api_specific_data: Optional[dict] = None
                ) -> None:
        super().__init__(bet_type, value, odds, bookmaker, lay, volume, previous_wager, wager)

        if update_time is None:
            update_time = datetime.now()
        self.update_time: datetime = update_time

        from arb_search.apis.base_api import API_Instance
        if api_specific_data is None:
            api_specific_data = {}
        self.api_specific_data: Dict[API_Instance, Dict[str, Any]] = api_specific_data    # type: ignore

    def update_from_bet(self, __new_bet: 'UserBet') -> 'UserBet':
        assert self.bookmaker == __new_bet.bookmaker
        assert self.bet_type == __new_bet.bet_type
        assert self.odds == __new_bet.odds

        if self.update_time < __new_bet.update_time:

            for key, value in self.api_specific_data.items():
                if key not in __new_bet.api_specific_data:
                    __new_bet.api_specific_data[key] = value
            self = __new_bet

        else:
            for key, value in __new_bet.api_specific_data.items():
                if key not in self.api_specific_data:
                    self.api_specific_data[key] = value

        return self
