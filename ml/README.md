# Analysis and dataset workflow

The current engine in api/analysis.py implements prototype persistence rules, a median/MAD descriptor, robust tilt slope and descriptive median-window shift. These are not trained ML or a collapse probability.

Stage 2 adds recording-session separation, sequence-gap handling, sample-time freshness and an operator-reviewed experiment archive. Open the Intelligence page to inspect sessions, annotate context and export JSON. Keep simulated examples separate from physical training data.

Run `python ml/benchmark.py` for deterministic synthetic regression scenarios. Run `python -m pytest tests -q` for system checks. Synthetic passes are not field accuracy or warning lead time.

Before training: collect calibrated independent experiments; include baseline, environmental/handling disturbance, movement and faults; review labels against independent observations; group all related nodes and sessions in the same split; hold out experiments and later time periods; report event-level false alarms, missed events, detection delay and uncertainty. Run candidate models in shadow mode. A model must never silently dismiss a configured movement warning.

Isolation Forest, sequence models, displacement forecasting and weather attribution are not loaded. `ml/evaluate.py` can split whole sessions into earlier and later partitions and score the rules on the held-out sessions. That report is not field accuracy. Shadow output cannot change an operational warning. An open incident does not replace the stored baseline. Model readiness counts are descriptive and do not establish sufficient training coverage.
