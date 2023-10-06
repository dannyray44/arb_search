import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type

from betting_event import Event

from . import UserBet, UserBookmaker

_rapid_api_key = json.load(open("settings/api_keys.json", "r"))["rapid-api"]

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
        self.score: float = 0

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

    def calculate_score(self) -> float:
        """Calculate the score of the event. Score is determined by the profit and the time to the start of the event."""
        if self.start_time is None:
            raise RuntimeError("Event has no start time")
        finish_time = self.start_time + timedelta(minutes= 100)
        time_to_finish = finish_time - datetime.now()
        repeatability = timedelta(days=1) / time_to_finish

        total_exposure = 0.0
        for bet in self.bets:
            if bet.lay:
                total_exposure += bet.wager * (bet.odds - 1)
            else:
                total_exposure += bet.wager

        if total_exposure != 0:
            profit_percent = 1 + (self.profit[0] / total_exposure)
            min_score = profit_percent ** repeatability
            # max_score = self.profit[1] ** repeatability
        else:
            min_score = 0.0

        self.score = min_score
        return self.score

    def get_name(self) -> str:
        """Get the name of the event."""
        api = list(self.api_specific_data.keys())[0]
        return " v ".join(api.read_event_comparison_data(self)[1:3]).replace('/', '-')

    def send_to_RapidAPI(self, api_key: str= _rapid_api_key, volume_percentage: float = 1.0) -> Event:
        for bet in self.bets:
            if bet.volume <= 0 or isinstance(bet.volume, str):
                continue
            bet.volume *= volume_percentage

        result = super().send_to_RapidAPI(api_key)

        for bet in self.bets:
            bet.volume /= volume_percentage
        
        return result

    def process(self) -> None:

        self.send_to_RapidAPI()
        self.calculate_score()
        if self.score == 0:
            return

        for _ in range(3):
            pass
