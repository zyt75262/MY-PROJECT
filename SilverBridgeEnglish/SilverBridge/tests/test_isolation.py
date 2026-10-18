import json, sqlite3, tempfile, threading, unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from community.server import build_server
ROOT=Path(__file__).resolve().parents[1]
class IsolationTests(unittest.TestCase):
    def test_app_identity_routes_and_database_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/'test.sqlite3';server=build_server(ROOT,db,0)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{server.server_port}'
            try:
                with urlopen(base+'/api/health') as r:self.assertEqual(json.load(r)['app'],'silverbridge')
                with urlopen(base+'/app.js') as r:
                    js=r.read().decode();self.assertNotIn('BrightBite',js);self.assertNotIn('data-action="app"',js)
                for path in ['/api/plans', '/api/favorites/oats']:
                    req=Request(base+path,data=b'{}',headers={'Content-Type':'application/json','X-Local-Request':'1'})
                    with self.assertRaises(HTTPError) as ctx:urlopen(req)
                    self.assertEqual(ctx.exception.code,404)
                with urlopen(base+'/api/state') as r:state=json.load(r)
                self.assertEqual(set(state).intersection({'tickets','recipes'}),{'tickets'})
                with sqlite3.connect(db) as conn:
                    actual={row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
                    self.assertEqual(actual,{'replies', 'stories', 'tickets'})
            finally:server.shutdown();server.server_close();thread.join(timeout=3)
