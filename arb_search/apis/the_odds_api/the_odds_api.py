
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import requests
from betting_event import BetType

from arb_search.sport_types import SportType
from arb_search.user_event import UserBet, UserBookmaker, UserEvent

from ..base_api import BaseAPI

from arb_search.utils import BookmakerStoredDict

class TheOddsAPI_V4(BaseAPI):

    def __init__(self, bookmaker_table: BookmakerStoredDict, default_start_time_range: Optional[Tuple[Optional[datetime], Optional[datetime]]] = None) -> None:
        super().__init__(name= 'the-odds-api', bookmaker_table= bookmaker_table)

        self.default_start_time_range = default_start_time_range

        self.default_params: dict = {'api_key': json.load(open("settings/api_keys.json", "r"))["the-odds-api"]}
        self.default_params.update(json.load(open(os.path.join(os.path.dirname(__file__), 'defaults.json')))["the-odds-api"])

        self.alternate_markets = ['alternate_spreads', 'alternate_totals', 'btts', 'draw_no_bet', 'h2h_3_way']
        self.requests_used: int = 0
        self.requests_remaining: int = 0

    def __call_api(self, endpoint: str, force_update: bool = False, params: Optional[dict] = None) -> dict:
        file_path = f'storage/the-odds-API_v4/{endpoint}.json'

        if params is None:
            params = self.default_params.copy()

        for key, value in params.items():
            if isinstance(value, list):
                params[key] = ','.join(value)

        if os.path.exists(file_path) and not force_update:
            with open(file_path, 'r') as f:
                result = json.load(f)
        else:
            response: requests.Response = requests.get(f'https://api.the-odds-api.com/v4/{endpoint}', params=params)
            if response.status_code != 200:
                raise Exception(f'Failed to get odds: status_code {response.status_code}, response body {response.text}')
            else:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                result = response.json()
                with open(file_path, 'w') as f:
                    json.dump(result, f, indent=2)

                if 'x-requests-used' in response.headers:
                    self.requests_used = int(round(float(response.headers['x-requests-used'])))
                if 'x-requests-remaining' in response.headers:
                    remaining_requests = int(round(float(response.headers['x-requests-remaining'])))
                    if self.requests_remaining != remaining_requests:
                        self.requests_remaining = remaining_requests
                        print(f'{self.requests_remaining} requests remaining')

        return result

    def _get_sports(self, force_update: bool = False, params: Optional[dict] = None) -> dict:
        return self.__call_api('sports', force_update=force_update, params=params)

    def _get_odds(self, sport_id: str, force_update: bool = False, params: Optional[dict] = None, start_time_range: Optional[Tuple[Optional[datetime], Optional[datetime]]] = None) -> dict:
        if start_time_range is None and self.default_start_time_range is not None:
            start_time_range = self.default_start_time_range
        if start_time_range is not None:
            force_update = True
            if params is None:
                params = self.default_params.copy()
            if start_time_range[0] is not None:
                params['commenceTimeFrom'] = start_time_range[0].isoformat(timespec='seconds') + 'Z'
            if start_time_range[1] is not None:
                params['commenceTimeTo'] = start_time_range[1].isoformat(timespec='seconds') + 'Z'
        return self.__call_api(f'sports/{sport_id}/odds', force_update=force_update, params=params)

    def _get_scores(self, sport_id: str, force_update: bool = False, params: Optional[dict] = None) -> dict:
        return self.__call_api(f'sports/{sport_id}/scores', force_update=force_update, params=params)

    def _get_historical_odds(self, sport_id: str, force_update: bool = False, params: Optional[dict] = None) -> dict:
        return self.__call_api(f'sports/{sport_id}/odds-history', force_update=force_update, params=params)

    def _get_event_odds(self, sport_key: str, event_id: str, force_update: bool = False, params: Optional[dict] = None) -> dict:
        """Get odds data for a specific event.
        [Additional markets](https://the-odds-api.com/sports-odds-data/betting-markets.html#additional-markets)
        can only be gathered through this endpoint.
        
        Args:
            sport_key (str): The sport ID.
            event_id (str): The event ID.
            force_update (bool): Whether to force API call or use saved data.
            params (dict): Additional parameters to pass to the API call. NOTE: Defaults to Additional Markets: ['alternate_spreads',
            'alternate_totals', 'btts', 'draw_no_bet', 'h2h_3_way'].
        """
        if params is None:
            params = self.default_params.copy()
            params["markets"] = self.alternate_markets
        return self.__call_api(f'sports/{sport_key}/events/{event_id}/odds', force_update=force_update, params=params)

    ###

    # def scan_sports_type(self, sport_types: List[SportType], start_time_range: Optional[Tuple[datetime, datetime]] = None) -> List[UserEvent]:
        
    #     #TODO: make this less wasteful: preselect sports before updating
    #     events = self.update_events(sport_types=[sport_types])
    #     if start_time_range is not None:
    #         events = [event for event in events if start_time_range[0] <= event.start_time <= start_time_range[1]]
    #     return events

    # def update_events(self,
    #                   events: Optional[List[UserEvent]] = None,
    #                   sport_types: Optional[List[Union[SportType, str]]] = None,
    #                   force_update: int = False
    #                   ) -> List[UserEvent]:
    #     """Get odds data for a list of events. Or get odds data for all events of a list of sport types.
        
    #     Args:
    #         events (List[UserEvent]): A list of events to update.
    #         sport_types (List[Union[SportType, str]]): A list of sport types to scan for events.
    #         force_update (int): Whether to force API call or use saved data. 0: use saved data, 1: force update, 2: force update and update sport types.
            
    #     Returns:
    #         List[UserEvent]: A list of events with updated odds.
    #     """

    #     available_sports = self._get_sports(force_update=(force_update>=2))
    #     valid_sport_types = set(sport["group"] for sport in available_sports)
    #     required_event_ids: Optional[List[str]] = None

    #     if events is None and sport_types is None:
    #         sport_types = valid_sport_types   # get all sports
    #         events = []
    #     elif events is not None and sport_types is None:
    #         sport_types = set(event.api_specific_data[self.name]["sport_group"] for event in events)
    #         required_event_ids = [event.api_specific_data[self.name]["id"] for event in events]
    #     elif events is None and sport_types is not None:
    #         events = []
    #         sport_types = [sport_type.name if isinstance(sport_type, SportType) else sport_type for sport_type in sport_types]
    #     else:
    #         raise Exception('Only one of events and sport_types can be specified')

    #     sport_types = list(filter(lambda sport_type: sport_type in valid_sport_types, sport_types))

    #     if sport_types is None:
    #         raise Exception(f'No valid sport types found. Valid sport types are: {valid_sport_types}')

    #     for i, available_sport in enumerate(available_sports):
    #         if available_sport["group"] not in sport_types:
    #             continue

    #         new_results = self._get_odds(available_sport["key"])

    #         for new_result in new_results:
    #             if required_event_ids and new_result["id"] not in required_event_ids:
    #                 continue

    #             alternate_odds = self._get_event_odds(available_sport["key"], new_result["id"])
    #             new_result["sport_group"] = available_sport["group"]
    #             new_result["bookmakers"] += alternate_odds["bookmakers"]

    #             if required_event_ids is None:
    #                 events.append(self._build_event(new_result))
    #             else:
    #                 events[required_event_ids.index(new_result["id"])].update_from_event(self._build_event(new_result), api_name= self.name)

    #         if i >= 42: #TODO: remove when done testing
    #             break

    #     return events

    def update_events(self, events: List[UserEvent]) -> List[UserEvent]:
       raise NotImplementedError
    
    def update_bet_data(self, event: UserEvent, bet_indexes: List[int]) -> bool:
        bets = [event.bets[i] for i in bet_indexes if hasattr(event.bets[i], 'api_specific_data') and self in event.bets[i].api_specific_data]
        if not bets:
            return False

        params = self.default_params.copy()
        params["markets"] = list(set(bet.api_specific_data[self]['market_key'] for bet in bets))
        odds = self._get_event_odds(event.api_specific_data[self]['sport_key'], event.api_specific_data[self]['id'], params=params, force_update=True)

        new_bets = self._build_bets(odds)

        print()

        return False

    def gather_events(self, sport_types: List[SportType], leagues: Optional[List[str]] = None, force_update: int = 0) -> List[UserEvent]:   #TODO: change force_update to 1
        available_sports = self._get_sports(force_update= (force_update >= 2))
        valid_sport_types = set(sport["group"] for sport in available_sports)
        sport_names = list(sport_type.name for sport_type in filter(lambda sport_type: sport_type.name in valid_sport_types, sport_types))

        if len(sport_names) == 0:
            raise Exception(f'No valid sport types found. Valid sport types are: {valid_sport_types}')

        events = []

        for available_sport in available_sports:
            if available_sport["key"] == 'soccer_netherlands_eredivisie':
                break

            if available_sport["group"] not in sport_names or leagues is not None and available_sport["key"] not in leagues:
                continue

            new_results = self._get_odds(available_sport["key"], force_update= (force_update >= 1))

            for new_result in new_results:
                alternate_odds = self._get_event_odds(available_sport["key"], new_result["id"], force_update= (force_update >= 1))
                new_result["sport_group"] = available_sport["group"]
                new_result["bookmakers"] += alternate_odds["bookmakers"]

                events.append(self._build_event(new_result))

        return events

    def _build_event(self, response: dict) -> UserEvent:
        compatible_event: UserEvent = UserEvent(start_time= datetime.fromisoformat(response['commence_time'].replace('Z', '')))
        compatible_event.add_bets(self._build_bets(response))
        compatible_event.api_specific_data[self] = self.extract_specific_data(response)
        return compatible_event

    def _build_bets(self, response: dict) -> List[UserBet]:
        bets = []

        for bookmaker in response["bookmakers"]:
            if bookmaker["key"] not in self.bookmaker_table:
                self.bookmaker_table[bookmaker["key"]] = UserBookmaker(name=bookmaker["key"])
                self.bookmaker_table.save()

            for market in bookmaker['markets']:
                update_time = datetime.fromisoformat(market['last_update'].replace('Z', ''))
                if market['key'] in ['h2h', 'h2h_lay']:
                    bet_type = BetType.MatchWinner
                    for outcome in market['outcomes']:
                        if outcome['name'] == response['home_team']:
                            value = 'home'
                        elif outcome['name'] == response['away_team']:
                            value = 'away'
                        elif outcome['name'].lower() == 'draw':
                            value = 'draw'
                        else:
                            raise Exception(f'Unknown outcome: {outcome}')

                        bets.append(UserBet(bet_type= bet_type, value= value, odds= outcome['price'],
                                            bookmaker= self.bookmaker_table[bookmaker['key']], lay= (market['key'] == 'h2h_lay'),
                                            update_time= update_time, api_specific_data= {self: {**outcome, **{'market_key': market['key']}}}))

                elif market['key'] == 'totals' or market['key'] == 'alternate_totals':
                    bet_type = BetType.Goals_OverUnder
                    for outcome in market['outcomes']:
                        value = outcome['name'].lower() + ' ' + str(outcome['point'])
                        bets.append(UserBet(bet_type= bet_type, value= value, odds= outcome['price'],
                                            bookmaker= self.bookmaker_table[bookmaker['key']], update_time= update_time,
                                            api_specific_data= {self: {**outcome, **{'market_key': market['key']}}}))

                elif market['key'] == 'btts':
                    bet_type = BetType.BothTeamsToScore
                    for outcome in market['outcomes']:
                        value = outcome['name'].lower()
                        bets.append(UserBet(bet_type= bet_type, value= value, odds= outcome['price'],
                                            bookmaker= self.bookmaker_table[bookmaker['key']], update_time= update_time,
                                            api_specific_data= {self: {**outcome, **{'market_key': market['key']}}}))

                elif market['key'] in ['draw_no_bet', 'spreads']:
                    bet_type = BetType.AsianHandicap
                    for outcome in market['outcomes']:
                        if outcome['name'] == response['home_team']:
                            value = 'home'
                        elif outcome['name'] == response['away_team']:
                            value = 'away'
                        else:
                            raise Exception(f'Unknown outcome: {outcome}')

                        if market['key'] == 'draw_no_bet':
                            value += ' 0.0'
                        elif market['key'] == 'spreads':
                            value += ' ' + str(outcome['point'])

                        bets.append(UserBet(bet_type= bet_type, value= value, odds= outcome['price'],
                                            bookmaker= self.bookmaker_table[bookmaker['key']], update_time= update_time,
                                            api_specific_data= {self: {**outcome, **{'market_key': market['key']}}}))

                else:
                    raise Exception(f'Unknown market: {market}')

        return bets

    def read_event_comparison_data(self, event: UserEvent) -> Tuple[str, str, str, str]: 
        return (self.name,
                event.api_specific_data[self]["home_team"],
                event.api_specific_data[self]["away_team"],
                event.api_specific_data[self]["sport_title"])

    @staticmethod
    def extract_specific_data(response: dict) -> dict:
        result = {}
        for key in ['id', 'sport_key', 'sport_title', 'sport_group', 'commence_time', 'home_team', 'away_team']:
            result[key] = response[key]
        return result
