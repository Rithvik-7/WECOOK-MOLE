from uuid import uuid4
from test_flow import client
HEADERS={'X-Mole-Capability':'test-token'}

def test_sos_retry_is_idempotent_and_private():
    packet={'request_id':str(uuid4()),'landmark':'private-gallery','message':'private-help','lat':12.3,'lon':77.2,'accuracy_m':25}
    first=client.post('/api/sos',json=packet)
    second=client.post('/api/sos',json=packet)
    assert first.status_code==200
    assert first.json()['id']==second.json()['id']
    assert second.json()['duplicate'] is True
    public=client.get('/api/state').json()['sos']
    row=next(r for r in public if r['id']==first.json()['id'])
    assert not {'landmark','message','lat','lon','contact'} & row.keys()
    assert client.get('/api/sos/operator').status_code==403
    inbox=client.get('/api/sos/operator',headers=HEADERS).json()['requests']
    assert next(r for r in inbox if r['id']==row['id'])['message']=='private-help'
    url=f"/api/sos/{row['id']}/acknowledge"
    assert client.post(url,json={'reason':'reviewed'}).status_code==403
    assert client.post(url,json={'reason':'Operator has read this request'},headers=HEADERS).json()['status']=='ACKNOWLEDGED'
    assert client.post(url,json={'reason':'repeat'},headers=HEADERS).status_code==409
    assert client.post('/api/sos',json=packet).json()['status']=='ACKNOWLEDGED'

def test_sos_location_validation():
    for packet in [{'lat':10},{'lat':95,'lon':0},{'lat':0,'lon':181},{'lat':0,'lon':0,'accuracy_m':-1},{'request_id':'invalid'}]:
        assert client.post('/api/sos',json=packet).status_code==422
