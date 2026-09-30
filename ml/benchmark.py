"""Reproducible synthetic rule checks, never a field accuracy estimate."""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'api'))
from analysis import classify_window, RULE_VERSION

def run():
    cases = {
        'steady': ([0, .02, -.02, .01, 0, .02], 'normal'),
        'single impulse': ([0, .02, 0, .01, 0, 4], 'watch'),
        'persistent rise': ([0, .02, 0, 1.3, 1.6, 1.9], 'movement'),
        'persistent fall': ([0, .02, 0, -1.3, -1.6, -1.9], 'movement'),
        'insufficient history': ([0, .1], 'unavailable'),
    }
    results = []
    for name, (values, expected) in cases.items():
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        rows = [{'tilt_deg': x, 'valid': True, 'origin':'simulated', 'sample_time': (start + timedelta(seconds=i*10)).isoformat()} for i,x in enumerate(values)]
        states = [classify_window(rows[:i+1], [])['condition'] for i in range(len(rows))]
        results.append({'scenario':name, 'expected':expected, 'actual':states[-1], 'passed':states[-1]==expected, 'first_movement_sample':next((i+1 for i,x in enumerate(states) if x=='movement'), None)})
    return {'rule_version':RULE_VERSION, 'scope':'Synthetic behavioral regression only. Not field accuracy or warning lead time.', 'results':results}

if __name__ == '__main__':
    result=run()
    print(json.dumps(result, indent=2))
    sys.exit(0 if all(x['passed'] for x in result['results']) else 1)
