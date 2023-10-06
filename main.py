from datetime import datetime, timedelta
from arb_search import API_Handler, TheOddsAPI_V4, SportType, Betfair, BookmakerStoredDict
import json
import threading
import os
import time
import shutil

# Delete the contents of the unprocessed folder
for folder in ['unprocessed', 'results']:
    shutil.rmtree(folder, ignore_errors= True)
    os.mkdir(folder)

profitable_events = []
threads = []

rapid_api_key = json.load(open("settings/api_keys.json", "r"))["rapid-api"]

# time_range_start = datetime(2023, 10, 3, 0, 0, 0, 0) 
time_range_start = datetime.now() - timedelta(hours=1)
time_range = (time_range_start, time_range_start + timedelta(hours=7))

bookmaker_table = BookmakerStoredDict()

the_odds_api = TheOddsAPI_V4(bookmaker_table, time_range)
# the_odds_api = TheOddsAPI_V4(bookmaker_table)
betfair_api = Betfair(bookmaker_table, time_range)

handler = API_Handler(apis= [the_odds_api]) #, betfair_api])

all_events = handler.gather_all_sport_type(sport_types= [SportType.Soccer], gather_new_leagues= True)

print(f"{len(all_events)} events found")

def save_to_file(event, output_folder: str = 'results', compact: bool = True):
    name = event.get_name()
    os.makedirs(output_folder, exist_ok=True)
    with open(f'{output_folder}/{name}.json', 'w') as f:
        json.dump(event.as_dict(compact), f, indent=4)

for event in all_events:
    event.wager_precision = 2
    save_to_file(event, "unprocessed", False)
    # x = threading.Thread(target= event.send_to_RapidAPI, args= (rapid_api_key, 0.8,))
    # threads.append(x)
    # x.start()
    # time.sleep(0.2)
    event.send_to_RapidAPI(rapid_api_key)
    print('+', end='', flush= True)
else:
    print()

# for thread in threads:
#     print('-', end='', flush= True)
#     if thread is None:
#         continue
#     thread.join()
# else:
#     print()

i = 0
while i < len(all_events):
    event = all_events[i]
    name = event.get_name()

    if event.profit != (0.0, 0.0):
        save_to_file(event= event)
        print(name)
        print(event.start_time)
        print(event.profit)
        print('----'*10)

    if event.profit == (0.0, 0.0):
        all_events.remove(event)
        continue

    event.calculate_score()

    i += 1

all_events.sort(key= lambda event: event.score, reverse= True)
for event in all_events:
    print("*************"*5)
    print(event.get_name())
    for _ in range(3):
        wager_indexes = [i for i in range(len(event.bets)) if event.bets[i].wager > 0]
        if handler.update_bet_data(event, wager_indexes):
            print("updates needed")
            event.send_to_RapidAPI(rapid_api_key, 0.5)
        else:
            break
    else:
        print("too many updates needed")
        continue

    save_to_file(event)
    print(event.profit)
    print('!')

print("done")
