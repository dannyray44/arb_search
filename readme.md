Demo arbitrage search tool for winwise.co.uk

This pulls in data from APIs:
- the_odds_api.com
- betfair.com (using betfairlightweight)
- (additional apis to be added)

The results from each API are a merged into a single list of event objects.
The event objects are sent to the winwise multi-market calculator to find arbitrage opportunities.
- They are sent via RapidAPI.com

Settings:
- Set your API keys in settings/api_keys.json


Disclaimer:
This is a demo tool that I wrote way too quickly. It is poorly documented and not well tested. I am not responsible for any losses you make using this tool. Use at your own risk.

If you have any questions about how to use this, or are interested in expanding on what is already here please contact me at dannyray44@hotmail.co.uk or via reddit r/winwise
