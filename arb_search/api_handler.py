import threading
from typing import Dict, List, Optional, Tuple, Type

from arb_search.apis.base_api import API_Instance
from arb_search.user_event.event import UserEvent

from .sport_types import SportType
from .utils import StoredDict, BookmakerStoredDict


class API_Handler:
    def __init__(self, apis: List[API_Instance], name_comparison_table: Optional[StoredDict] = None, bookmaker_table: Optional[BookmakerStoredDict] = None) -> None:
        self.apis: List[API_Instance] = apis
    
        if name_comparison_table is None:
            name_comparison_table = StoredDict('storage/API_terminology_db.pkl')
        self.name_comparison_table: StoredDict = name_comparison_table

        if bookmaker_table is None:
            bookmaker_table = BookmakerStoredDict()
        self.bookmaker_table: BookmakerStoredDict = bookmaker_table

        for api in self.apis:
            if api.name not in self.name_comparison_table:
                self.name_comparison_table[api.name] = {"team_names": {}, "league_names": {}}

    def gather_all_sport_type(self, sport_types: List[SportType], gather_new_leagues: bool= False) -> List[UserEvent]:
        apis_events: Dict[API_Instance, List[UserEvent]] = {} # type: ignore

        for api in self.apis:
            league_names = list(self.name_comparison_table[api.name]["league_names"].values())
            if gather_new_leagues:
                league_names = None
            # TODO: add threading
            apis_events[api] = api.gather_events(sport_types= sport_types, leagues= league_names)


        return self.match_events(apis_events)


    def update_bet_data(self, event: UserEvent, bet_indexes: List[int]) -> bool:
        recalculation_needed = False
        for api in event.api_specific_data.keys():
            recalculation_needed |= api.update_bet_data(event, bet_indexes)

        return recalculation_needed


    def match_events(self, apis_events: Dict[API_Instance, List[UserEvent]]) -> List[UserEvent]:
        apis_list = list(apis_events.keys())

        for api_1 in apis_list[:-1]:
            for api_2 in apis_list[apis_list.index(api_1) + 1:]:

                event_1_idx = 0
                while event_1_idx < len(apis_events[api_1]):

                    event_2_idx = -1
                    while event_2_idx < len(apis_events[api_2]) - 1:
                        event_2_idx += 1

                        event_1 = apis_events[api_1][event_1_idx]
                        event_2 = apis_events[api_2][event_2_idx]

                        if self.events_match((event_1, event_2), (api_1, api_2)):
                            event_1.update_from_event(event_2, api_2)
                            del apis_events[api_2][event_2_idx]
                            break

                    event_1_idx += 1
        
        return [event for events in apis_events.values() for event in events]

    def events_match(self, events: Tuple[UserEvent, UserEvent], apis: Tuple[API_Instance, API_Instance]) -> bool:
        """Return True if the events match, False otherwise."""

        default_index = 0

        home_common_names = []
        away_common_names = []
        league_common_names = []

        if events[0].start_time != events[1].start_time:
            return False

        api_names, home_names, away_names, league_names = zip(*[api.read_event_comparison_data(event) for api, event in zip(apis, events)])
        api_names = list(api_names)
        home_names = list(home_names)
        away_names = list(away_names)
        league_names = list(league_names)

        new_value = False
        i = 0
        for api_name, home_name, away_name, league_name in zip(api_names, home_names, away_names, league_names):

            if api_name not in self.name_comparison_table:
                print(f"Adding {api_name} to name matching data")
                self.name_comparison_table[api_name] = {"team_names": {}, "league_names": {}}

            if i == default_index:
                self.name_comparison_table[api_name]["team_names"][home_name] = home_name
                self.name_comparison_table[api_name]["team_names"][away_name] = away_name
                self.name_comparison_table[api_name]["league_names"][league_name] = league_name

            if home_name in self.name_comparison_table[api_name]["team_names"]:
                home_common_names.append(self.name_comparison_table[api_name]["team_names"][home_name])
            else:
                new_value = True

            if away_name in self.name_comparison_table[api_name]["team_names"]:
                away_common_names.append(self.name_comparison_table[api_name]["team_names"][away_name])
            else:
                new_value = True

            if league_name in self.name_comparison_table[api_name]["league_names"]:
                league_common_names.append(self.name_comparison_table[api_name]["league_names"][league_name])
            else:
                new_value = True

            i += 1

        self.name_comparison_table.save()

        if len(set(home_common_names)) == 1 and len(set(away_common_names)) == 1 and len(set(league_common_names)) == 1:
            if not new_value:
                return True

            if self.user_verify(api_names, home_names, away_names, league_names) is True:
                i= -1
                for api_name, home_name, away_name, league_name in zip(api_names, home_names, away_names, league_names):
                    i += 1
                    if i == default_index:
                        continue
                    self.name_comparison_table[api_name]["team_names"][home_name] =     self.name_comparison_table[api_names[default_index]]["team_names"][home_names[default_index]]
                    self.name_comparison_table[api_name]["team_names"][away_name] =     self.name_comparison_table[api_names[default_index]]["team_names"][away_names[default_index]]
                    self.name_comparison_table[api_name]["league_names"][league_name] = self.name_comparison_table[api_names[default_index]]["league_names"][league_names[default_index]]

                self.name_comparison_table.save()
                return True
        return False

    def user_verify(self, api_names: List[str], home_names: List[str], away_names: List[str], league_names: List[str]) -> bool:
        # print('!', end='')
        # return False
        buffer = 5
        api_width = max(len(api_name) for api_name in api_names) + buffer
        home_width = max(len(home_name) for home_name in home_names) + buffer
        away_width = max(len(away_name) for away_name in away_names) + buffer
        league_width = max(len(league_name) for league_name in league_names) + buffer

        print(f"+-{'-'*api_width}+-{'-'*home_width}+-{'-'*away_width}+-{'-'*league_width}+")
        print(f"| {'API Name':<{api_width}}| {'Home':<{home_width}}| {'Away':<{away_width}}| {'League':<{league_width}}|")
        print(f"|-{'-'*api_width}|-{'-'*home_width}|-{'-'*away_width}|-{'-'*league_width}|")
        for row in zip(api_names, home_names, away_names, league_names):
            print(f"| {row[0]:<{api_width}}| {row[1]:<{home_width}}| {row[2]:<{away_width}}| {row[3]:<{league_width}}|")
        print(f"+-{'-'*api_width}+-{'-'*home_width}+-{'-'*away_width}+-{'-'*league_width}+")

        for _ in range(100):
            inp = input("Do these events match? yes:(y), no:(n) or exit:(e) ")

            if inp == 'y':
                return True
            elif inp == 'n':
                return False
            elif inp == 'e':
                raise SystemExit
            else:
                print("Invalid input")
        
        raise SystemExit

