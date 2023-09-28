from datetime import datetime, timezone
from typing import Optional
from betfairlightweight.metadata import list_market_book

def datetime_to_betfair_format(datetime_var: datetime) -> str:
    return datetime_var.replace(tzinfo=None).isoformat(timespec='milliseconds') + 'Z'

def betfair_to_datetime(betfair_datetime: str) -> datetime:
    return datetime.fromisoformat(betfair_datetime[:-1]).replace(tzinfo=None)


def price_projection_weight(__price_projection: Optional[dict]) -> int:
    if __price_projection is not None:
        result = sum([list_market_book[price_data] for price_data in __price_projection['priceData']])

        if "EX_BEST_OFFERS" in __price_projection['priceData'] and "EX_TRADED" in __price_projection['priceData']:
            result -= 2

        if "EX_ALL_OFFERS" in __price_projection['priceData'] and "EX_TRADED" in __price_projection['priceData']:
            result -= 2

    else:
        result = list_market_book['']

    if __price_projection and "exBestOffersOverrides" in __price_projection and 'bestPricesDepth' in __price_projection['exBestOffersOverrides']:
        result *= int(__price_projection['exBestOffersOverrides']['bestPricesDepth']) / 3

    if isinstance(result, float) and not result.is_integer():
        result = divmod(result, 1)[0] + 1   # round up

    return int(result)