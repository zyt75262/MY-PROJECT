import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from community.server import build_server

ROOT = Path(__file__).resolve().parents[1]


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = build_server(ROOT, Path(cls.temp.name) / "api.sqlite3", 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temp.cleanup()

    def request(self, path, payload=None, headers=None):
        body = None if payload is None else json.dumps(payload).encode()
        request_headers = {"Content-Type": "application/json", "X-Local-Request": "1"}
        request_headers.update(headers or {})
        request = Request(self.url + path, data=body, headers=request_headers)
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            content_type = response.headers.get("Content-Type", "")
            return response.status, json.loads(raw) if "json" in content_type else raw, response.headers

    def test_app_assets_health_and_private_files(self):
        for path, mime in (("/", "text/html"), ("/app.js", "javascript"), ("/styles.css", "text/css")):
            status, body, headers = self.request(path)
            self.assertEqual(status, 200)
            self.assertIn(mime, headers["Content-Type"])
            self.assertTrue(body)
        self.assertEqual(self.request("/api/health")[1]["mode"], "local_demo")
        self.assertEqual(self.request("/../README.md")[0], 404)
        self.assertEqual(self.request("/local_data/community.sqlite3")[0], 404)

    def test_plan_replace_feedback_and_export(self):
        status, plan, _ = self.request("/api/plans", {"budget": 30, "days": 3, "allergies": ["花生", "蛋"]})
        self.assertEqual(status, 201)
        prefix = "/api/plans/" + plan["id"]
        status, choices, _ = self.request(prefix + "/replacements?day=0&meal=0&position=0")
        self.assertEqual(status, 200)
        identifier = choices["recipes"][0]["id"]
        status, updated, _ = self.request(prefix + "/replace", {"day": 0, "meal": 0, "position": 0, "recipe_id": identifier})
        self.assertEqual(status, 200)
        self.assertEqual(updated["days"][0]["meals"][0]["ids"][0], identifier)
        self.assertEqual(self.request(prefix + "/feedback", {"feedback": "想尝试"})[1]["feedback"], "想尝试")
        status, body, headers = self.request(prefix + "/export")
        self.assertEqual(status, 200)
        self.assertIn("Demonstration meal plan", body.decode("utf-8"))
        self.assertIn("attachment", headers["Content-Disposition"])


    def test_origin_and_input_validation(self):
        self.assertEqual(self.request("/api/health", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.request("/api/plans", {}, {"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.request("/api/plans", {}, {"X-Local-Request": ""})[0], 403)
        self.assertEqual(self.request("/api/plans", {"budget": True})[0], 400)
        self.assertEqual(self.request("/api/plans", {"budget": 1})[0], 400)
        self.assertEqual(self.request("/api/state")[0], 200)


    def test_health_explanation_create_replace_reload_and_export(self):
        status,plan,_=self.request('/api/plans',{'budget':60,'preferred_ids':['milk'],'seed':7})
        self.assertEqual(status,201)
        self.assertIn('milk',plan['days'][0]['meals'][0]['ids'])
        self.assertIn('bones',{p['id'] for p in plan['days'][0]['health_support']})
        prefix='/api/plans/'+plan['id']
        position=plan['days'][0]['meals'][0]['ids'].index('milk')
        status,changed,_=self.request(prefix+'/replace',{'day':0,'meal':0,'position':position,'recipe_id':'soy'})
        self.assertEqual(status,200)
        self.assertNotIn('bones',{p['id'] for p in changed['days'][0]['health_support']})
        state=self.request('/api/state')[1]
        self.assertEqual(state['plan']['days'][0]['health_support'],changed['days'][0]['health_support'])
        source=next(r for r in state['source_recipes'] if r['number']==40)
        # Original claims about reducing myopia are not used as nutrition evidence.
        self.assertNotIn('vision',{p['id'] for p in source['health_support']})
        self.assertIn('Body functions and health context',self.request(prefix+'/export')[1].decode())
        self.assertTrue(all('health_support' in r for r in state['recipes']))


if __name__ == "__main__":
    unittest.main()
