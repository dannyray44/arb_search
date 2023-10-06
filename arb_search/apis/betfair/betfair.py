import json
import threading
from time import sleep
from datetime import datetime, timedelta
from os import path
from typing import Dict, Iterator, List, Optional, Tuple, Union

from betfairlightweight import APIClient, filters
from betfairlightweight.filters import price_projection

from arb_search.apis.base_api import API_Instance, BaseAPI
from arb_search.apis.utils import fixed_count_bin_packer
from arb_search.sport_types import SportType
from arb_search.user_event import UserBet, UserBookmaker, UserEvent
from arb_search.utils import BookmakerStoredDict, StoredDict, team_name_matcher

from betting_event import BetType

from .endpoints.betting import Betting_Limitless
from .utils import (betfair_to_datetime, datetime_to_betfair_format,
                    price_projection_weight)

MARKET_TYPE_CODES = {
    1: ['MATCH_ODDS', 'MATCH_ODDS_UNMANAGED',
        'ASIAN_HANDICAP', 'ODD_OR_EVEN', 
        'CORRECT_SCORE', #'CORRECT_SCORE2',
        'OVER_UNDER_05', 'OVER_UNDER_15', 'OVER_UNDER_25', 'OVER_UNDER_35', 'OVER_UNDER_45', 'OVER_UNDER_55', 'OVER_UNDER_65', 'OVER_UNDER_75', 'OVER_UNDER_85',
        'TEAM_A_OVER_UNDER_05', 'TEAM_A_OVER_UNDER_15', 'TEAM_A_OVER_UNDER_25', 'TEAM_A_OVER_UNDER_35', 'TEAM_B_OVER_UNDER_05', 'TEAM_B_OVER_UNDER_15', 'TEAM_B_OVER_UNDER_25', # 'TEAM_B_OVER_UNDER_35'
        # 'MATCH_ODDS_AND_OU_05', 'MATCH_ODDS_AND_OU_15', 
        'MATCH_ODDS_AND_OU_25', 'MATCH_ODDS_AND_OU_35',
        # TODO: figure out what these are 'TEAM_A_1', 'TEAM_A_2', 'TEAM_A_3', 'TEAM_B_1', 'TEAM_B_2', 'TEAM_B_3',
        # TODO: Implement bet class w/ ID 91: 'ALT_TOTAL_GOALS', 'COMBINED_TOTAL', 'TOTAL_GOALS'  
        'TEAM_A_WIN_TO_NIL', 'TEAM_B_WIN_TO_NIL',
        'BOTH_TEAMS_TO_SCORE', 'MATCH_ODDS_AND_BTTS',
        # TODO: Implement ID 47? 'DRAW_NO_BET',
        'DOUBLE_CHANCE']
        # TODO merge ID 27 and 28 'CLEAN_SHEET']           #'HANDICAP'
}

class Betfair(BaseAPI, APIClient):
    def __init__(self, bookmaker_table: BookmakerStoredDict, default_start_time_range: Optional[Tuple[datetime, datetime]] = None) -> None:

        APIClient.__init__(self, **json.load(open('settings/api_keys.json', 'r'))["betfair_api"], lightweight= True)
        BaseAPI.__init__(self, "betfair", bookmaker_table)

        self.bookmaker_name = "betfair_ex_uk"
        if self.bookmaker_name not in bookmaker_table:
            bookmaker_table[self.bookmaker_name] = UserBookmaker(self.bookmaker_name)

        settings = json.load(open('settings/settings.json', 'r'))["apis"]["betfair"]

        if default_start_time_range is None:
            default_start_time_range = (datetime.now(), datetime.now() + timedelta(hours=settings["default_hours_range"]))
        self.default_start_time_range = default_start_time_range

        self._competitions_table = StoredDict('storage/betfair/competitions.pkl')

        self.betting = Betting_Limitless(self)
        self.login()

    def gather_events(self, sport_types: List[SportType], leagues: Optional[List[str]] = None, start_time_range: Optional[Tuple[datetime, datetime]] = None) -> List[UserEvent]:
        events_table: Dict[str, UserEvent] = {}
        market_type_codes: List[str] = []

        for sport_type in sport_types:
            market_type_codes += MARKET_TYPE_CODES[sport_type.value]
        market_type_codes = list(set(market_type_codes))

        if start_time_range is None:
            start_time_range = self.default_start_time_range

        market_filter = filters.market_filter(
            event_type_ids= [sport_type.value for sport_type in sport_types],
            market_type_codes= market_type_codes,
            market_start_time= {
                "from": datetime_to_betfair_format(start_time_range[0]),
                "to": datetime_to_betfair_format(start_time_range[1])
            }
        )

        if leagues is not None:
            competition_ids = [self._competitions_table[league] for league in leagues]
            market_filter.update(filters.market_filter(competition_ids= competition_ids))

        # all market projections
        # market_projection = ['COMPETITION', 'EVENT', 'EVENT_TYPE', 'MARKET_START_TIME', 'MARKET_DESCRIPTION', 'RUNNER_DESCRIPTION', 'RUNNER_METADATA']

        markets = self.betting.list_all_market_catalogue(filter=market_filter, market_projection=['EVENT', 'COMPETITION', 'RUNNER_DESCRIPTION'])

        for market in markets:
            if not market["event"]["id"] in events_table:
                events_table[market["event"]["id"]] = UserEvent(start_time= betfair_to_datetime(market["event"]["openDate"]),
                                                          bookmakers= [self.bookmaker_table[self.bookmaker_name]],
                                                          api_specific_data= {self: {**market["event"], **{"markets": {}, "total_runner_count": 0}}}
                                                         ) #TODO: figure out no_draw


            if "competition" not in events_table[market["event"]["id"]].api_specific_data[self] and "competition" in market:
                events_table[market["event"]["id"]].api_specific_data[self]["competition"] = market["competition"]

            events_table[market["event"]["id"]].api_specific_data[self]["markets"][market["marketId"]] = {
                "marketName": market["marketName"],
                "totalMatched": market["totalMatched"],
                "runners": market["runners"]
            }

            events_table[market["event"]["id"]].api_specific_data[self]["total_runner_count"] += len(market["runners"])

        return self.update_events(list(events_table.values()))

    def update_bet_data(self, event: UserEvent, bet_indexes: List[int]) -> bool:
        new_bets: List[UserBet] = []
        bet_indexes.sort()
        updates_needed = False
        bets = [event.bets[index] for index in bet_indexes]
        market_books = self.betting.list_market_book(
            [bet.api_specific_data[self]["market_id"] for bet in bets if self in bet.api_specific_data and "market_id" in bet.api_specific_data[self]],
            price_projection= price_projection(price_data=['EX_BEST_OFFERS']),
            order_projection= 'EXECUTABLE')
        
        for market_book in market_books:
            for current_runner, new_runner in zip(event.api_specific_data[self]["markets"][market_book['marketId']]["runners"], market_book["runners"]):
                assert current_runner["selectionId"] == new_runner["selectionId"]
                new_runner.update(current_runner)
            new_bets.extend(self._build_bets(event, market_book)) # type: ignore
        
        
        for old_index in bet_indexes[::-1]:
            old_bet = event.bets[old_index]
            if old_bet not in new_bets:
                updates_needed = True
                event.bets.remove(old_bet)
            else:
                new_bet = new_bets[new_bets.index(old_bet)]
                new_bet.wager = old_bet.wager
                new_bet.previous_wager = old_bet.previous_wager
                if old_bet.wager > new_bet.volume:
                    updates_needed = True
                event.add_bet(new_bet)

        return updates_needed

    def update_events(self, events: List[UserEvent]) -> List[UserEvent]:
        price_projection_dict = price_projection(price_data=['EX_BEST_OFFERS'])
        market_id_runners_table: Dict[str, int] = {}

        for event in events:
            for market_id in event.api_specific_data[self]["markets"].keys():
                market_id_runners_table[market_id] = event.api_specific_data[self]["total_runner_count"]

        all_market_books = self.betting.list_all_market_book(market_id_runners_table, price_projection= price_projection_dict, order_projection= 'EXECUTABLE', lightweight= True)

        for event in events:
            new_bets = []
            for market_id in event.api_specific_data[self]["markets"].keys():
                market_book = all_market_books.pop(market_id)
                for current_runner, new_runner in zip(event.api_specific_data[self]["markets"][market_book['marketId']]["runners"], market_book["runners"]):
                    assert current_runner["selectionId"] == new_runner["selectionId"]
                    new_runner.update(current_runner)
                # for new_bet in self._build_bets(event, market_book):
                #     event.add_bet(new_bet)
                new_bets.extend(self._build_bets(event, market_book))

            if event.bets == []:
                event.bets = new_bets
            else:
                for new_bet in new_bets:
                    event.add_bet(new_bet)

        return events
    
    def read_event_comparison_data(self, event: UserEvent) -> Tuple[str, str, str, str]:
        result = [self.name]
        result += [name.strip() for name in event.api_specific_data[self]["name"].split(' v ')]
        result += [event.api_specific_data[self]["competition"]["name"]]
        if len(result) != 4:
            raise ValueError("Expected 4 values in result, but got {}".format(len(result)))
        return tuple(result) # type: ignore

    def _build_bets(self, event: UserEvent, market_book: dict) -> List[UserBet]:
        bets_list = []
        market_data = event.api_specific_data[self]["markets"][market_book['marketId']]

        _home_team, _away_team = event.api_specific_data[self]["name"].split(' v ')

        team_table = {
            _home_team.lower(): "home",
            _away_team.lower(): "away",
            "the draw": "draw",
            "draw": "draw"
        }

        team_names = list(team_table.keys())

        if not market_data["marketName"] == "Asian Handicap" and any(runner["handicap"] != 0.0 for runner in market_data["runners"]):
            raise ValueError(f"Non-zero handicap in non-asian handicap market {market_data['marketName']}")

        if market_data["marketName"].startswith("Over/Under ") and market_data["marketName"].endswith(" Goals"):
            bet_type = BetType.Goals_OverUnder
            bet_values = [runner["runnerName"][:-6].lower() for runner in market_data["runners"]]
            # exchanges = [runner["ex"] for runner in market_book["runners"]]

        elif market_data["marketName"] == "Match Odds":
            bet_type = BetType.MatchWinner
            bet_values = [team_table[team_name_matcher(runner["runnerName"], team_names)] for runner in market_data["runners"]]

        elif market_data["marketName"] == "Double Chance":
            bet_type = BetType.DoubleChance
            bet_values = [runner["runnerName"].lower().replace(' or ', '/') for runner in market_data["runners"]]

        elif market_data["marketName"] == "Correct Score":
            bet_type = BetType.ExactScore
            bet_values = [runner["runnerName"].replace(' - ', ':') for runner in market_data["runners"] if not runner["runnerName"].startswith('Any')] #TODO: don't discard 'Any Other Score'

        elif market_data["marketName"] == "Asian Handicap":
            bet_type = BetType.AsianHandicap
            bet_values = [f'{team_table[team_name_matcher(runner["runnerName"], team_names)]} {runner["handicap"]}' for runner in market_data["runners"]]
            # remove values that start with "draw"
            bet_value = [value for value in bet_values if not value.startswith("draw")] # TODO: figure out how to implement this for betfair

        elif market_data["marketName"] == "Both teams to Score?":
            bet_type = BetType.BothTeamsToScore
            bet_values = [runner["runnerName"].lower() for runner in market_data["runners"]]

        # elif market_data["marketName"].lower().endswith(" win to nil"):
        #     bet_type = BetType.Team_WinToNil
        #     bet_values = [f'{team_table[team_name_matcher(market_data["marketName"][:-11].lower(), team_names)]} {runner["runnerName"].lower()}' for runner in market_data["runners"]]

        elif market_data["marketName"] == "Match Odds and Both teams to Score":
            bet_type = BetType.Result_BothTeamsScore
            bet_values = [team_table[team_name_matcher(runner["runnerName"][:runner["runnerName"].index("/")].lower(), team_names)] + runner["runnerName"][runner["runnerName"].index("/"):].lower() for runner in market_data["runners"]]

        elif market_data["marketName"] == "Total Goals Odd/Even":
            bet_type = BetType.OddEven
            bet_values = [runner["runnerName"].lower() for runner in market_data["runners"]]

        elif market_data["marketName"].startswith("Match Odds and Over/Under") and market_data["marketName"].endswith(" Goals"):
            bet_type = BetType.Result_OverUnder
            bet_values = [f'{team_table[team_name_matcher(runner["runnerName"][:runner["runnerName"].index("/")].lower(), team_names)]}/{runner["runnerName"][runner["runnerName"].index("/") + 1:-6].lower()}' for runner in market_data["runners"]]

        elif market_data["marketName"].lower().startswith(_home_team.lower()) or market_data["marketName"].lower().startswith(_away_team.lower()):
            if market_data["marketName"].lower().startswith(_home_team.lower()):
                rest_of_name = market_data["marketName"][len(_home_team) + 1:]
                team = "home"
            else:
                rest_of_name = market_data["marketName"][len(_away_team) + 1:]
                team = "away"

            if rest_of_name.startswith("Over/Under ") and rest_of_name.endswith(" Goals"):
                bet_type = BetType.Team_OverUnder
                bet_values = [f"{team} {runner['runnerName'][:-6].lower()}" for runner in market_data["runners"]]

            elif rest_of_name.lower() == "win to nil":
                bet_type = BetType.Team_WinToNil
                bet_values = [f'{team} {runner["runnerName"].lower()}' for runner in market_data["runners"]]

            else:
                raise ValueError(f"Unknown market type '{market_data['marketName']}'")

        else:
            raise ValueError(f"Unknown market type '{market_data['marketName']}'")

        for runner_index, (bet_value, ex) in enumerate(zip(bet_values, [runner["ex"] for runner in market_book["runners"]])):
            for market_key in ex:
                if market_key not in ["availableToBack", "availableToLay"]:
                    continue    #TODO: add previous_wager here
                for price in ex[market_key]:
                    bets_list.append(
                        UserBet(
                            bet_type= bet_type,
                            value= bet_value,
                            odds= price["price"],
                            bookmaker= self.bookmaker_table[self.bookmaker_name],
                            lay= (market_key == "availableToLay"),
                            volume= price["size"],
                            api_specific_data= {
                                self: {
                                    "market_id": market_book['marketId'],
                                    "selection_id": market_book['runners'][runner_index]['selectionId']
                                }
                            }
                        )
                    )

        return bets_list
