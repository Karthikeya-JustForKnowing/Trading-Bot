# Trading-Bot
A small Python application that can place orders on Binance Futures Testnet (USDT-M) and provide a clean, reusable structure with proper logging and error handling.

Small Python CLI application for placing `MARKET`, `LIMIT`, and bonus `STOP` / `STOP_MARKET` orders on Binance USDT-M Futures Testnet.

## Features

- Places `MARKET` and `LIMIT` orders on Binance Futures Testnet
- Supports both `BUY` and `SELL`
- Validates CLI input before sending requests
- Clean separation between CLI, API client, validation, and order logic
- Structured rotating log file for requests, responses, and errors
- Bonus support for `STOP` and `STOP_MARKET` orders

## Project Structure

```text
project/
├── bot/
│   ├── __init__.py
│   ├── client.py
│   ├── config.py
│   ├── exceptions.py
│   ├── logging_config.py
│   ├── orders.py
│   └── validators.py
├── logs/
├── .env.example
├── cli.py
├── README.md
└── requirements.txt
```

## Setup

1. Create and activate a Python 3.10+ virtual environment.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and replace the placeholder values with your Binance Futures Testnet credentials.

```powershell
Copy-Item .env.example .env
```

4. Make sure your Binance account is a **Futures Testnet** account and that the base URL stays:

```text
https://testnet.binancefuture.com
```

## Environment Variables

```env
BINANCE_API_KEY=replace_with_testnet_api_key
BINANCE_API_SECRET=replace_with_testnet_api_secret
BINANCE_BASE_URL=https://testnet.binancefuture.com
```

You can also override the credentials directly with CLI flags:

```powershell
python cli.py --symbol BTCUSDT --side BUY --order-type MARKET --quantity 0.001 --api-key YOUR_KEY --api-secret YOUR_SECRET
```

## Usage

### MARKET order

```powershell
python cli.py --symbol BTCUSDT --side BUY --order-type MARKET --quantity 0.001
```

### LIMIT order

```powershell
python cli.py --symbol BTCUSDT --side SELL --order-type LIMIT --quantity 0.001 --price 120000 --time-in-force GTC
```

### Bonus STOP order

```powershell
python cli.py --symbol BTCUSDT --side BUY --order-type STOP --quantity 0.001 --price 110000 --stop-price 109500 --time-in-force GTC
```

### Bonus STOP_MARKET order

```powershell
python cli.py --symbol BTCUSDT --side SELL --order-type STOP_MARKET --quantity 0.001 --stop-price 95000
```

## Example Output

```text
Order request summary
---------------------
Symbol        : BTCUSDT
Side          : BUY
Order Type    : MARKET
Quantity      : 0.001

Order response
--------------
Order ID      : 123456789
Status        : FILLED
Symbol        : BTCUSDT
Side          : BUY
Type          : MARKET
Original Qty  : 0.001
Executed Qty  : 0.001
Average Price : 103500.00

Success: order request was accepted by Binance Futures Testnet.
Log file: logs/trading_bot.log
```

## Logging

- Runtime logs are written to [logs/trading_bot.log](./logs/trading_bot.log)
- The file includes:
  - outgoing API requests
  - API responses
  - validation failures
  - network errors
  - Binance API errors

The console only shows warnings/errors so CLI output stays clean.

## Assumptions

- The evaluator will provide valid Binance Futures Testnet API credentials.
- Quantity and price precision are accepted by Binance for the chosen symbol.
- The account has enough virtual balance and permissions to place futures orders.

## Notes

- `MARKET` and `LIMIT` satisfy the must-have task requirements.
- `STOP` and `STOP_MARKET` are included as the optional bonus.
- Actual order log entries are generated when you run the commands with your real testnet credentials.
