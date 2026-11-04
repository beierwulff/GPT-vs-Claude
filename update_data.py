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
    with open(DATA_FILE, encoding='utf-8') as file:
        data = json.load(file)

    is_open = market_open(now)
    if not is_open and data.get('marketData', {}).get('updatedAtUTC'):
        print('NYSE closed; retaining the last successfully calculated portfolio snapshot.')
        return
    if not is_open:
        print('NYSE closed and no saved snapshot exists; recovering the latest daily closing prices.')

    tickers = {h['ticker'] for side in ('gpt', 'claude') for h in data.get(side, {}).get('holdings', [])}
    fx = get_json('https://open.er-api.com/v6/latest/USD')
    if fx.get('result') != 'success':
        raise RuntimeError('Currency feed failed')
    usd_dkk = float(fx['rates']['DKK'])
    prices = {}
    quote_times = []
    for ticker in sorted(tickers):
        interval, period = ('1m', '1d') if is_open else ('1d', '10d')
        quote = get_json(f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={period}')
        result = quote['chart']['result'][0]
        meta = result['meta']
        if meta.get('currency') != 'USD':
            raise ValueError(f'{ticker}: expected USD, got {meta.get("currency")}')
        # Prefer most recent intraday close, falling back to quoted market price.
        closes = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
        valid = [float(p) for p in closes if p is not None]
        # A completed daily candle is the last regular-session close, not an after-hours quote.
        # During the session prefer Yahoo's latest regular-market quote; outside
        # the session retain the most recent completed daily close.
        price = (meta.get('regularMarketPrice') if is_open else None) or (valid[-1] if valid else None) or meta.get('previousClose')
        if price is None or float(price) <= 0:
            raise ValueError(f'No usable price for {ticker}')
        prices[ticker] = float(price)
        timestamps = result.get('timestamp') or []
        if timestamps:
            quote_time = datetime.fromtimestamp(timestamps[-1], timezone.utc)
            if not is_open:
                ny = quote_time.astimezone(ZoneInfo('America/New_York'))
                quote_time = ny.replace(hour=16, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
            quote_times.append(quote_time)

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
    # Keep a real portfolio-value time series. Each successful market fetch
    # adds one point; this preserves the opening/closing observations over time.
    history = data.get('history', [])
    if not isinstance(history, list):
        history = []
    point = {
        'timestamp': now.isoformat(),
        'gpt': round(float(data.get('gpt', {}).get('portfolioValue', 0)), 2),
        'claude': round(float(data.get('claude', {}).get('portfolioValue', 0)), 2),
        'snapshotType': 'intraday' if is_open else 'last_close'
    }
    # Avoid duplicate snapshots if the workflow is manually rerun immediately.
    if not history or history[-1].get('timestamp') != point['timestamp']:
        history.append(point)
    # Retain up to roughly 90 days of five-minute market observations.
    data['history'] = history[-26000:]

    # During bootstrap after closing, distinguish fetch time from quote time.
    data['marketData'] = {'updatedAtUTC': now.isoformat(), 'snapshotType': 'intraday' if is_open else 'last_close', 'asOfUTC': min(quote_times).isoformat() if quote_times else now.isoformat(), 'usdDkk': usd_dkk,
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
