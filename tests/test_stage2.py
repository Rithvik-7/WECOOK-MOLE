from datetime import datetime, timezone, timedelta
from test_flow import client

HEADERS = {'X-Mole-Capability':'test-token'}

def packet(session, sequence=0, **extra):
    return {'node_id':'D','session_id':session,'sequence':sequence,'origin':'physical','sample_time':datetime.now(timezone.utc).isoformat(),'tilt_deg':.2, **extra}

def test_packet_contract_and_origin_isolation():
    assert client.post('/api/telemetry',json=packet('contract',sample_time='yesterday')).status_code == 422
    assert client.post('/api/telemetry',json=packet('contract',sample_time='2026-01-01T00:00:00')).status_code == 422
    assert client.post('/api/telemetry',json=packet('contract',sequence=-1)).status_code == 422
    assert client.post('/api/telemetry',json=packet('contract')).status_code == 200
    assert client.post('/api/telemetry',json=packet('contract',sequence=1,origin='simulated')).status_code == 409

def test_session_baseline_isolation_and_ordered_replay():
    for seq in [0,2,1]:
        client.post('/api/telemetry',json=packet('ordered',sequence=seq))
    node=next(n for n in client.get('/api/state').json()['nodes'] if n['id']=='D')
    assert [r['sequence'] for r in node['history']]==[0,1,2]
    assert all(r['session_id']=='ordered' for r in node['history'])
    old=(datetime.now(timezone.utc)-timedelta(days=10)).isoformat()
    client.post('/api/telemetry',json=packet('old-replay',sample_time=old))
    node=next(n for n in client.get('/api/state').json()['nodes'] if n['id']=='D')
    assert node['latest']['session_id']=='ordered'

def test_archive_review_export_and_access():
    path='/api/experiments/D/ordered'
    assert client.post(path+'/review',json={'label':'baseline','note':'Bench reference'}).status_code==403
    assert client.post(path+'/review',json={'label':'baseline','note':'Bench reference'},headers=HEADERS).status_code==200
    export=client.get(path+'/export').json()
    assert export['annotation']['label']=='baseline'
    assert len(export['readings'])==3
    assert all(r['origin']=='physical' for r in export['readings'])
    assert client.get('/api/experiments').json()['readiness']['trained_model'] is False

def test_linear_sensor_is_retained_without_inventing_units():
    assert client.post('/api/telemetry',json=packet('linear-check',node_id='C',linear_raw=123)).status_code==200
    node=next(n for n in client.get('/api/state').json()['nodes'] if n['id']=='C')
    assert node['latest']['linear_raw']==123
    assert 'not confirmed' in node['latest']['linear_note']
    assert node['latest']['potentiometer_mm'] is None

def test_stale_replay_is_not_fresh():
    old=(datetime.now(timezone.utc)-timedelta(minutes=3)).isoformat()
    # future sequence in current session still carries old observation time.
    client.post('/api/telemetry',json=packet('ordered',sequence=3,sample_time=old))
    node=next(n for n in client.get('/api/state').json()['nodes'] if n['id']=='D')
    assert node['analysis']['quality']['freshness']=='stale'
    assert node['condition']=='stale'

def test_no_sos_delivery_claim_and_whitespace_review():
    result=client.post('/api/sos',json={'message':'test request','delivered':True})
    assert result.status_code==200
    assert result.json()['status']=='QUEUED'
    assert client.post('/api/incidents/no-such-id/acknowledge',json={'reason':'   '},headers=HEADERS).status_code==422
