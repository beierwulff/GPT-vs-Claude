import json
import os
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=15) as response:
        return json.load(response)

def market_open(now):
    # NYSE calendar: US holidays and early closes are handled by exchange_calendars.
    import exchange_calendars as xcals
    exchange = xcals.get_calendar('XNYS')
    return exchange.is_open_on_minute(now, ignore_breaks=True)

def main():
    now = datetime.now(timezone.utc)
    if not market_open(now):
        print('NYSE closed; keeping last known values.')
        return

    with open(DATA_FILE, encoding='utf-8') as file:
        data = json.load(file)

    tickers = {h['ticker'] for side in ('gpt', 'claude') for h in data.get(side, {}).get('holdings', [])}
    fx = get_json('https://open.er-api.com/v6/latest/USD')
    if fx.get('result') != 'success':
        raise RuntimeError('Currency feed failed')
    usd_dkk = float(fx['rates']['DKK'])
    prices = {}
    for ticker in sorted(tickers):
        quote = get_json(f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d')
        result = quote['chart']['result'][0]
        meta = result['meta']
        if meta.get('currency') != 'USD':
            raise ValueError(f'{ticker}: expected USD, got {meta.get("currency")}')
        # Prefer most recent intraday close, falling back to quoted market price.
        closes = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
        valid = [float(p) for p in closes if p is not None]
        price = meta.get('regularMarketPrice') or (valid[-1] if valid else None)
        if price is None or float(price) <= 0:
            raise ValueError(f'No usable price for {ticker}')
        prices[ticker] = float(price)

    for side in ('gpt', 'claude'):
        account = data.get(side)
        if not account:
            continue
        holdings_total = 0.0
        for h in account.get('holdings', []):
            value = float(h['qty']) * prices[h['ticker']] * usd_dkk
            cost = float(h['costBaseDKK'])
            h['currentVal'] = round(value, 2)
            h['returnPct'] = round((value / cost - 1) * 100, 2) if cost else 0.0
            holdings_total += value
        cash = float(account.get('cashDKK', 0))
        dividends = float(account.get('netDividendsDKK', 0))
        # Dividends already reinvested are part of holdings, not extra value.
        # Cash includes uninvested dividends and must not be counted again.
        portfolio_value = holdings_total + cash
        invested = float(account.get('investedTotal', 0))
        account['portfolioValue'] = round(portfolio_value, 2)
        account['profit'] = round(portfolio_value - invested, 2)
        account['returnPct'] = round(100 * (portfolio_value - invested) / invested, 2) if invested else 0.0
    data['marketData'] = {'updatedAtUTC': now.isoformat(), 'usdDkk': usd_dkk,
                          'pricesUSD': prices, 'source': 'Yahoo Finance / open.er-api.com',
                          'note': 'Indicative, not Trading 212 executable prices'}
    temp = DATA_FILE + '.tmp'
    with open(temp, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write('\n')
    os.replace(temp, DATA_FILE)
    print('Portfolio updated:', data['marketData']['updatedAtUTC'])

if __name__ == '__main__':
    main()
