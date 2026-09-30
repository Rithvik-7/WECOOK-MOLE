"""Reproducible synthetic-only 20-second ridge benchmark. Not field validation."""
from pathlib import Path
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HORIZONS = [5, 10, 15, 20]

def dataset(seed, count):
    rng = np.random.default_rng(seed)
    x, y = [], []
    for _ in range(count):
        t = np.arange(160, dtype=float)
        kind = rng.integers(0, 4)
        slope = rng.uniform(-.015, .015)
        signal = slope*t + rng.uniform(.03, .3)*np.sin(t/rng.uniform(18, 90)+rng.uniform(0, 6))
        if kind == 1:
            signal += rng.uniform(-.00008, .00008)*t*t
        if kind == 2:
            signal += rng.uniform(-.6, .6)*(t > rng.integers(40, 130))
        if kind == 3:
            signal = np.zeros_like(t)
        signal += rng.normal(0, rng.uniform(.002, .035), len(t))
        for end in [40, 65, 90, 115]:
            window = signal[end-19:end+1]
            scale = max(float(np.std(window)), .01)
            x.append([1., *((window-window[-1])/scale).tolist()])
            y.append(((signal[end+np.array(HORIZONS)]-window[-1])/scale).tolist())
    return np.array(x), np.array(y)

def main():
    x,y = dataset(20260928, 700)
    cx,cy = dataset(20260929, 180)
    tx,ty = dataset(20260930, 200)
    penalty = np.eye(x.shape[1])*20
    penalty[0,0] = 0
    coef = np.linalg.solve(x.T@x+penalty, x.T@y)
    radius = np.quantile(np.abs(cy-cx@coef), .9, axis=0)
    predicted = tx@coef
    report = {
        'training_scope':'synthetic signals only; no mine or hardware validation',
        'split':'disjoint generated sessions: train / calibration / test',
        'sessions':{'train':700,'calibration':180,'test':200},
        'test_mae_normalized':np.mean(np.abs(predicted-ty),axis=0).tolist(),
        'persistence_mae_normalized':np.mean(np.abs(ty),axis=0).tolist(),
        'test_band_coverage':np.mean(np.abs(predicted-ty)<=radius,axis=0).tolist(),
        'units':'window standard deviations; not degrees or probability of collapse',
    }
    model = {'version':'synthetic-ridge-20s-v1','horizons_seconds':HORIZONS,'window':20,
             'cadence_seconds':1,'coefficients':coef.tolist(),'residual_radius':radius.tolist(),
             'report':report,'operational_warnings':False}
    target=ROOT/'web/public/models/short-horizon.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(model,indent=2),encoding='utf-8')
    (ROOT/'ml/short-horizon-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
