"""Independent clients without login, races and restart persistence."""
import base64
import concurrent.futures
import http.cookiejar
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler, Request

from community.server import build_server
from community.storage import Storage

ROOT=Path(__file__).resolve().parents[1]

class SharingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/'test.sqlite3'
        Storage(self.db).create_story({'title':'旧草稿','body':'不得自动分享到网络'})
        self.start()
        self.a=self.client();self.b=self.client()

    def client(self):
        return build_opener(ProxyHandler({}), HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def start(self):
        self.server=build_server(ROOT,self.db,0,host='0.0.0.0')
        self.url=f'http://127.0.0.1:{self.server.server_port}'
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)

    def tearDown(self):
        self.stop();self.temp.cleanup()

    def request(self,client,path,payload=None,headers=None):
        raw=None if payload is None else json.dumps(payload).encode()
        h={'Content-Type':'application/json','X-Local-Request':'1',**(headers or {})}
        req=Request(self.url+path,data=raw,headers=h)
        try:r=client.open(req,timeout=5)
        except HTTPError as e:r=e
        with r:
            body=r.read();return r.status,json.loads(body) if 'json' in r.headers.get('Content-Type','') else body

    def test_direct_access_and_origin_checks(self):
        self.assertEqual(self.request(self.a,'/api/state')[0],200)
        self.assertEqual(self.request(self.b,'/api/shared')[0],200)
        status,ticket=self.request(self.a,'/api/tickets',{'category':'其他问题','body':'无需登录提交'})
        self.assertEqual(status,201)
        self.assertEqual(self.request(self.b,'/api/shared')[1]['tickets'][0]['id'],ticket['id'])
        self.assertEqual(self.request(self.a,'/api/session',{})[0],404)
        self.assertEqual(self.request(self.a,'/api/tickets',{}, {'Origin':'http://evil.test'})[0],403)
        self.assertEqual(self.request(self.a,'/api/state',headers={'Host':'evil.test'})[0],403)
        self.assertEqual(self.request(self.a,'/api/tickets',{}, {'X-Local-Request':''})[0],403)

    def test_two_clients_attachment_claim_reply_resolve_restart(self):
        image='data:image/png;base64,'+base64.b64encode(b'fake-image-for-round-trip').decode()
        status,t=self.request(self.a,'/api/tickets',{'category':'手机操作','body':'怎么发照片','image':image})
        self.assertEqual(status,201)
        self.assertEqual(self.request(self.b,'/api/shared')[1]['tickets'][0]['image'],image)
        prefix=f"/api/tickets/{t['id']}"
        # Transactions must allow exactly one winner when two devices claim at once.
        with concurrent.futures.ThreadPoolExecutor() as pool:
            futures=[pool.submit(self.request,c,prefix+'/claim',{}) for c in (self.a,self.b)]
            self.assertEqual(sorted(f.result()[0] for f in futures),[200,409])
        self.assertEqual(self.request(self.b,prefix+'/reply',{'body':'点击聊天窗口右下角的加号'})[0],200)
        self.assertEqual(self.request(self.a,'/api/shared')[1]['tickets'][0]['replies'][0]['body'],'点击聊天窗口右下角的加号')
        self.assertEqual(self.request(self.a,prefix+'/resolve',{})[0],200)
        self.assertEqual(self.request(self.b,'/api/shared')[1]['tickets'][0]['status'],'done')
        self.stop();self.start()
        self.assertEqual(self.request(self.a,'/api/shared')[1]['tickets'][0]['status'],'done')

    def test_story_consent(self):
        state=self.request(self.a,'/api/state')[1]
        self.assertEqual(state['stories'],[])
        self.assertEqual(self.request(self.a,'/api/stories',{'title':'故事','body':'新故事'})[0],400)
        self.assertEqual(self.request(self.a,'/api/stories',{'title':'故事','body':'新故事','share':True})[0],201)
        self.assertEqual(len(self.request(self.b,'/api/shared')[1]['stories']),1)

    def test_stale_session_cookie_is_ignored(self):
        self.assertEqual(self.request(self.a,'/api/state',headers={'Cookie':'community_session=old-expired-token'})[0],200)
        self.assertEqual(self.request(self.b,'/api/health')[1]['mode'],'shared')

    def test_image_only_request(self):
        image='data:image/png;base64,'+base64.b64encode(b'screenshot').decode()
        self.assertEqual(self.request(self.a,'/api/tickets',{'category':'手机操作','image':image})[0],201)

if __name__=='__main__':unittest.main()
