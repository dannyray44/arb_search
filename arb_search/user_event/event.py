import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from betting_event import Event

# from ..apis.base_api import API_Instance, BaseAPI
from . import UserBet, UserBookmaker

# from arb_search.apis.base_api import API_Instance



class UserEvent(Event):
    _BOOKMAKER_CLASS = UserBookmaker
    _BET_CLASS = UserBet
    DEFAULTS = json.load(open("settings/event_defaults.json", "r"))["event"]

    def __init__(self,
                 wager_limit: float = DEFAULTS["wager_limit"],
                 wager_precision: float = DEFAULTS["wager_precision"],
                 profit: list[float] = [0.0, 0.0],
                 no_draw: bool = False,
                 bookmakers: Optional[List[UserBookmaker]] = None,
                 bets: Optional[List[UserBet]] = None,
                 start_time: Optional[datetime] = None,
                 api_specific_data: Optional[Dict['API_Instance', Dict[str, Any]]] = None
                ) -> None:

        super().__init__(wager_limit, wager_precision, profit, no_draw, bookmakers, bets)

        self.start_time: Optional[datetime] = start_time
        if api_specific_data is None:
            api_specific_data = {}
        self.api_specific_data: Dict['API_Instance', Dict[str, Any]] = api_specific_data

        self.bets: List[UserBet]
        self.bookmakers: List[UserBookmaker]

    def update_from_event(self, __new_event: 'UserEvent', api: 'API_Instance') -> 'UserEvent':
        current_bet_indexes = list(range(len(self.bets)))
        self.bookmakers = __new_event.bookmakers

        for new_bet in __new_event.bets:
            for i in current_bet_indexes:
                if self.bets[i] == new_bet:
                    self.bets[i] = self.bets[i].update_from_bet(new_bet)
                    break
            else:
                self.bets.append(new_bet)
                continue

            current_bet_indexes.remove(i)

        for i in current_bet_indexes[::-1]:
            if api in self.bets[i].api_specific_data.keys():
                del self.bets[i]

        return self
