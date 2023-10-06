from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Type, TypeVar

from arb_search.sport_types import SportType
from arb_search.user_event import UserEvent
from arb_search.utils import BookmakerStoredDict


class BaseAPI(ABC):
    def __init__(self, name: str, bookmaker_table: BookmakerStoredDict):
        self.name = name
        self.bookmaker_table = bookmaker_table

    @abstractmethod
    def gather_events(self, sport_types: List[SportType], leagues: Optional[List[str]] = None) -> List[UserEvent]:
        pass

    @abstractmethod
    def update_events(self, events: List[UserEvent]) -> List[UserEvent]:
        pass

    @abstractmethod
    def update_bet_data(self, event: UserEvent, bet_indexes: List[int]) -> bool:
        pass

    @abstractmethod
    def read_event_comparison_data(self, event: UserEvent) -> Tuple[str, str, str, str]:
        """For the given event attempt to recover the api_name, home_team_name, away_team_name & league_name."""
        pass

class BaseBookmakerAPI(BaseAPI):
    @abstractmethod
    def place_bet(self, event: UserEvent, bet_index: int) -> bool:
        pass

class BaseExchangeAPI(BaseBookmakerAPI):
    @abstractmethod
    def update_matched_wager_status(self, event: UserEvent, bet_index: int) -> bool:
        pass

API_Instance = TypeVar('API_Instance', bound=BaseAPI)
