from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from analysis import classify_window, robust_z

def samples(values):
    start = datetime(2026, 9, 27, tzinfo=timezone.utc)
    return [{"tilt_deg":v,"valid":True,"origin":"simulated","sample_time":(start+timedelta(minutes=i)).isoformat()} for i,v in enumerate(values)]

def test_isolated_spike_does_not_satisfy_persistence():
    result=classify_window(samples([0,.01,0,.01,0,2]),[])
    assert result["condition"]=="watch"
    assert result["features"]["sustained_samples"]==1

def test_movement_and_gas_remain_separate():
    data=samples([0,.01,0,1.4,1.5,1.6])
    data[-1].update(gas_raw=2100,gas_ready=True)
    result=classify_window(data,[])
    assert result["condition"]=="movement"
    assert result["gas_state"]=="gas"
    assert result["features"]["sustained_samples"]==3

def test_fault_does_not_erase_previous_movement_evidence():
    data=samples([0,.01,0,1.4,1.5,1.6,None])
    data[-1].update(valid=False,fault=True)
    result=classify_window(data,[])
    assert result["condition"]=="movement"
    assert result["fault_active"] is True
    assert result["quality"]["valid_count"]==6

def test_invalid_gap_breaks_persistence():
    data=samples([0,0,0,1.4,1.5,None,1.6])
    data[5]["valid"]=False
    result=classify_window(data,[])
    assert result["condition"]=="watch"
    assert result["features"]["sustained_samples"]==1

def test_reversed_times_do_not_produce_a_rate():
    data=samples([0,0,0,1.3,1.4,1.6])
    data[-1]["sample_time"]=data[0]["sample_time"]
    assert classify_window(data,[])["features"]["slope_deg_min"] is None

def test_even_median_and_constant_reference():
    assert robust_z(4,[0,1,2,3]) > 1.68
    assert robust_z(4,[1,1,1]) is None

def test_stale_cannot_be_normal():
    data=samples([0,0,0,0,0,0]);data[-1]["stale"]=True
    assert classify_window(data,[])["condition"]=="stale"

def test_no_nan_leaks_into_features():
    data=samples([0,0,0,float("nan")])
    r=classify_window(data,[])
    assert r["condition"]=="sensor_fault"
    assert r["quality"]["valid_count"]==3

def test_repeated_invalid_tail_retains_movement():
    samples=[{'tilt_deg':v,'valid':True} for v in [0,0,0,1.3,1.4,1.5]]
    samples += [{'valid':False,'tilt_deg':None}, {'valid':False,'tilt_deg':None}]
    result=classify_window(samples,[])
    assert result['movement_state']=='movement'
    assert result['fault_active'] is True


def test_missing_sequence_breaks_persistence():
    samples=[{'tilt_deg':v,'valid':True,'sequence':i} for i,v in zip([0,1,2,3,5,6],[0,0,0,1.3,1.4,1.5])]
    assert classify_window(samples,[])['movement_state']=='watch'
