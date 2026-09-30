import importlib.util
import io
import json
import urllib.error
from pathlib import Path
spec=importlib.util.spec_from_file_location('mole_gateway',Path(__file__).resolve().parents[1]/'gateway'/'gateway.py')
gateway=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)

class Reply:
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self): return json.dumps({'duplicate':True}).encode()

def test_rejected_packet_does_not_block_following_packet(tmp_path,monkeypatch):
    monkeypatch.setattr(gateway,'QUEUE',tmp_path/'queue.db')
    gateway.enqueue({'sequence':0})
    gateway.enqueue({'sequence':1})
    def respond(request,timeout):
        if json.loads(request.data)['sequence']==0:
            raise urllib.error.HTTPError('http://local',422,'invalid',{},io.BytesIO(b'invalid packet'))
        return Reply()
    monkeypatch.setattr(gateway.urllib.request,'urlopen',respond)
    result=gateway.sync()
    assert result['sent']==1 and result['rejected_this_sync']==1 and result['pending']==0
    assert gateway.sync()['sent']==0

def test_outage_retains_queue_and_original_packet(tmp_path,monkeypatch):
    monkeypatch.setattr(gateway,'QUEUE',tmp_path/'queue.db')
    gateway.enqueue({'sample_time':'2026-01-01T00:00:00Z','sequence':1})
    def fail(*args,**kwargs): raise OSError('offline')
    monkeypatch.setattr(gateway.urllib.request,'urlopen',fail)
    assert gateway.sync()['pending']==1
    with gateway.connect() as conn:
        assert json.loads(conn.execute('SELECT body FROM outbound').fetchone()[0])['sample_time']=='2026-01-01T00:00:00Z'
