import http.client
import threading

from gangnamfly.server import LocalServer, handler


class Runtime:
    model = None
    demo = None

    def read(self):
        return {"status": "idle"}

    def submit(self, action, episode):
        if action not in ["train", "observe", "replay", "pause"]:
            raise ValueError("Invalid action")


# AC: AC-5
def test_server_rejects_foreign_origin_traversal_and_bad_commands(tmp_path):
    Runtime.root = tmp_path
    server = LocalServer(("127.0.0.1", 0), handler(Runtime(), 0))
    port = server.server_address[1]
    server.RequestHandlerClass = handler(Runtime(), port)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()

    def request(method, path, body=None, **headers):
        conn = http.client.HTTPConnection("127.0.0.1", port)
        conn.request(method, path, body, headers)
        response = conn.getresponse()
        response.read()
        conn.close()
        return response.status

    try:
        assert request("GET", "/api/state") == 200
        assert request("GET", "/api/evidence/../../secret") == 404
        assert request("GET", "/api/evidence/20260909T120000-abcdef12") == 404
        assert request("GET", "/api/evidence/20260909T120000-abcdef12", Origin="https://evil.example") == 403
        assert request("GET", "/api/state", Origin="https://evil.example") == 403
        assert request("GET", "/api/state", Host="evil.example") == 403
        assert request("GET", "/assets/../../pyproject.toml") == 404
        assert request("GET", "/api/model") == 503
        assert request("GET", "/api/demo") == 503
        assert request("GET", "/api/demo", Origin="https://evil.example") == 403
        assert (
            request("POST", "/api/command", '{"action":"train"}', **{"Content-Type": "application/json"})
            == 202
        )
        assert (
            request("POST", "/api/command", '{"action":"delete"}', **{"Content-Type": "application/json"})
            == 400
        )
        assert request("POST", "/api/command", "{}") == 415
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
