# Fluxion ML

Models and inference service used by the Fluxion backend for liquidity forecasting, supply chain demand forecasting, financial risk scoring, transaction anomaly detection and compliance screening.

## Layout

```
ml_models/
  config/        constants.py (feature schemas, training profiles), settings.py (service environment)
  core/          artifacts.py (versioned save/load), registry.py (versions, A/B routing, metrics), training.py (trainer)
  data/          pipeline.py (market feature pipeline), features.py (risk and transaction features), synthetic.py (bootstrap data)
  networks/      architectures.py (all torch modules)
  forecasting/   liquidity.py, supply_chain.py, common.py
  risk/          risk_model.py, compliance.py
  anomaly/       detector.py (autoencoder plus isolation forest)
  serving/       service.py (ModelService), app.py (routes), handlers.py, metrics.py, server.py
  cli/           train.py
  tests/         unit/ and integration/
  docs/          api.md
```

Dependencies point one way: `serving` and `cli` depend on the domain packages, domain packages depend on `core`, `data`, `networks` and `config`, and `config` depends on nothing.

## Models

| Type         | Input                               | Output                                             | Architecture                              |
| ------------ | ----------------------------------- | -------------------------------------------------- | ----------------------------------------- |
| liquidity    | hourly market records               | next 6 periods of pool liquidity with 90% interval | bidirectional LSTM with attention         |
| supply_chain | 30 periods of supply chain features | next 5 periods of demand with 90% interval         | CNN, LSTM and attention                   |
| risk         | 50 or more hourly market records    | five risk factors and an overall score             | bidirectional LSTM with attention         |
| anomaly      | transactions                        | anomaly score and flag                             | autoencoder blended with isolation forest |
| compliance   | transactions                        | probability for six violation types                | multi-label MLP                           |

Intervals come from held-out residual quantiles, not fixed percentage bands.

## Training data

The repository contains no labeled production data. On first start the service trains every model that has no active version using synthetic data (`ML_AUTO_BOOTSTRAP`, `ML_BOOTSTRAP_PROFILE`). The risk and compliance labels are rule-derived from the inputs, so their offline metrics describe how well the network reproduces those rules, not real-world detection accuracy. Retrain on real data before relying on the outputs:

```
python -m ml_models.cli.train --model-dir models --profile full \
  --data liquidity=pool_history.csv anomaly=transactions.json
```

Data files are CSV or JSON lists of records using the field names in `config/constants.py`.

## Running

```
pip install -r requirements.txt
python -m ml_models.serving
python -m ml_models.cli.train --profile quick --model-dir models
```

Run both commands from the directory that contains the `ml_models` folder, or install the package with `pip install .`.

## Configuration

| Variable             | Default     | Purpose                                      |
| -------------------- | ----------- | -------------------------------------------- |
| MODEL_PATH           | /app/models | artifact and registry directory              |
| PORT                 | 8000        | API port                                     |
| METRICS_PORT         | 9091        | Prometheus metrics port                      |
| ML_SERVICE_API_KEY   | empty       | when set, required in the `X-API-Key` header |
| ML_AUTO_BOOTSTRAP    | true        | train missing models at start                |
| ML_BOOTSTRAP_PROFILE | full        | `full` or `quick`                            |
| LOG_LEVEL            | info        | logging level                                |

## Development

```
make install
make test
make lint
make format
```
