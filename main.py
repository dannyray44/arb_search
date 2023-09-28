from datetime import datetime, timedelta
from arb_search import API_Handler, TheOddsAPI_V4, SportType, Betfair, BookmakerStoredDict
import json

rapid_api_key = json.load(open("settings/api_keys.json", "r"))["rapid-api"]

time_range_start = datetime(2023, 9, 30 , 12, 30, 0, 0) 
time_range_start = datetime.now() - timedelta(hours=1)
time_range = (time_range_start, time_range_start + timedelta(hours=25))

bookmaker_table = BookmakerStoredDict()

the_odds_api = TheOddsAPI_V4(bookmaker_table, time_range)
# the_odds_api = TheOddsAPI_V4(bookmaker_table)
betfair_api = Betfair(bookmaker_table, time_range)

handler = API_Handler(apis= [betfair_api, the_odds_api])

all_events = handler.gather_all_sport_type(sport_types= [SportType.Soccer], gather_new_leagues= True)

print(f"{len(all_events)} events found")

for event in all_events:
    for _ in range(3):
        event.send_to_RapidAPI(rapid_api_key)
        if event.profit == (-444, -444):
            continue


    if event.profit != (0.0, 0.0):
        if betfair_api in event.api_specific_data:
            name = event.api_specific_data[betfair_api]["name"]
        elif the_odds_api in event.api_specific_data:
            name = the_odds_api.read_event_comparison_data(event)[0]
        else:
            raise RuntimeError("No API found")
        
        with open(f'results/{name}.json', 'w') as f:
            json.dump(event.as_dict(), f, indent=4)


        print('----'*10, end='')
        print(event.start_time)
        print(event.profit)



print("done")
