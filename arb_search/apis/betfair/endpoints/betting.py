from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from time import sleep
from typing import Dict, Iterator, List, Optional, Union

import requests
from betfairlightweight import metadata, resources
from betfairlightweight.endpoints import Betting
from betfairlightweight.filters import market_filter
from betfairlightweight.metadata import list_market_book
from ..utils import price_projection_weight

class Betting_Limitless(Betting):

    def list_all_market_catalogue(
            self,
            filter: dict = market_filter(),
            market_projection: Optional[list] = None,
            locale: Optional[str] = None,
            session: Optional[requests.Session] = None,
            lightweight: bool = True
        ) -> Union[list, List[resources.MarketCatalogue]]:

        max_results: int = 1000
        results: Dict[str, dict] = {}
        from_str = ''

        if market_projection is not None:
            request_weight = sum([metadata.list_market_catalogue.get(key, 0) for key in market_projection])
            if request_weight != 0:
                max_results = 200 // request_weight
        else:
            market_projection = []

        if 'EVENT' not in market_projection:
            market_projection.append('EVENT')   # required for openDate

        if not 'marketStartTime' in filter:
            filter['marketStartTime'] = {}

        for i in range(1, 100):
            if i%5 == 0:
                sleep(0.2)

            newest_results: list = super().list_market_catalogue(filter, market_projection, 'FIRST_TO_START', max_results, locale, session, lightweight) # type: ignore

            if not newest_results: 
                break

            new_finds = False
            for new_result in newest_results:
                if not new_result['marketId'] in results:
                    results[new_result['marketId']] = new_result
                    new_finds = True

            if new_finds:
                from_str = (datetime.fromisoformat(newest_results[-1]['event']['openDate'][:-1])).isoformat(timespec='milliseconds') + 'Z'
                # from_str = datetime_to_betfair_format(betfair_to_datetime(newest_results[-1]['event']['openDate']))
                filter['marketStartTime'].update({'from': from_str})
                # sleep(0.2)                                              #TODO: implement better solution
                continue
            break
        else:
            raise RuntimeError('i actually reached limit')

        return list(results.values())

    def list_all_market_book(
            self,
            market_id_runners_table: Dict[str, int],
            price_projection: Optional[dict] = None,
            order_projection: Optional[str] = None,
            match_projection: Optional[str] = None,
            include_overall_position: Optional[bool] = None,
            partition_matched_by_strategy_ref: Optional[bool] = None,
            customer_strategy_refs: Optional[list] = None,
            currency_code: Optional[str] = None,
            matched_since: Optional[str] = None,
            bet_ids: Optional[list] = None,
            locale: Optional[str] = None,
            session: Optional[requests.Session] = None,
            lightweight: bool = True
        ) -> Dict[str, dict]:
        results = {}

        weight = price_projection_weight(price_projection)
        chunk_size = 200 // weight

        with ThreadPoolExecutor() as executor:
            futures = []

            for market_ids in self._market_and_runner_limiter(market_id_runners_table, chunk_size):
                futures.append(executor.submit(super().list_market_book, market_ids, price_projection, order_projection, match_projection, include_overall_position, partition_matched_by_strategy_ref, customer_strategy_refs, currency_code, matched_since, bet_ids, locale, session, lightweight))

            for future in as_completed(futures):
                market_books = future.result()
                results.update({market_book['marketId']: market_book for market_book in market_books})

        return results

    @staticmethod
    def _market_and_runner_limiter(market_id_runners_table: Dict[str, int], max_market_count: int, max_runners: int = 250) -> Iterator[List[str]]:
        market_count = 0
        runner_count = 0

        market_ids: List[str] = []

        for market_id, market_runners_count in market_id_runners_table.items():
            market_count += 1
            runner_count += market_runners_count
            if market_count >= max_market_count or market_runners_count >= max_runners:
                yield market_ids
                market_count = 1
                runner_count = market_runners_count
                market_ids = []

            market_ids.append(market_id)

        if market_ids:
            yield market_ids

