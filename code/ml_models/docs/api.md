# ML service API

All paths except `/health` and `/ready` require the `X-API-Key` header when `ML_SERVICE_API_KEY` is set. Bodies are JSON objects. An optional `X-Request-ID` header makes A/B model selection deterministic per request.

| Method | Path                      | Body                      | Notes                                                          |
| ------ | ------------------------- | ------------------------- | -------------------------------------------------------------- |
| GET    | /health                   | none                      | liveness                                                       |
| GET    | /ready                    | none                      | 200 when every model type has an active version, otherwise 503 |
| GET    | /v1/models                | none                      | active versions, metrics, usage, training state                |
| POST   | /v1/liquidity/forecast    | records, horizon (1 to 6) | at least 120 hourly records                                    |
| POST   | /v1/supply-chain/forecast | records, horizon (1 to 5) | at least 30 records                                            |
| POST   | /v1/risk/assess           | records                   | at least 50 hourly records                                     |
| POST   | /v1/anomalies/detect      | transactions              | up to 5000                                                     |
| POST   | /v1/compliance/check      | transactions              | up to 5000                                                     |
| POST   | /v1/transactions/screen   | transactions              | anomaly and compliance combined                                |
| POST   | /v1/models/train          | models, profile           | returns 202, runs in the background                            |

Status codes: 401 missing or wrong key, 409 training already running, 413 body over 8 MiB, 422 invalid input, 503 models not ready.

Market records: `timestamp`, `price`, `volume`, `liquidity`, with optional `utilization`, `collateral_ratio`, `verified`.

Transactions: `amount` is required. Optional: `timestamp`, `avg_amount_30d`, `tx_count_24h`, `tx_count_30d`, `account_age_days`, `kyc_score`, `country_risk`, `counterparties_30d`, `cross_border`.
