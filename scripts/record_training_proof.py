"""Record nine real short trials, explicitly labeled as a technical smoke test.

Run from the project root. Requires Playwright Chromium; writes only local files.
"""

import gzip
import json
import resource
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from playwright.sync_api import expect, sync_playwright

from gangnamfly.runtime import Runtime
from gangnamfly.server import LocalServer, handler

root = Path("episodes/proof-" + time.strftime("%Y%m%dT%H%M%S"))
runtime = Runtime(root, auto=False, training_seconds=1.0)
server = LocalServer(("127.0.0.1", 8766), handler(runtime, 8766))
worker = threading.Thread(target=server.serve_forever, daemon=True)
worker.start()
try:
    deadline = time.monotonic() + 120
    while runtime.read()["status"] == "loading":
        if time.monotonic() > deadline:
            raise RuntimeError("load timeout")
        time.sleep(0.1)
    assert runtime.read()["status"] == "idle", runtime.read()
    print("READY", root, flush=True)
    clip = json.loads(gzip.decompress(runtime.demo))
    Path("docs/evidence/retarget-report.json").write_text(
        json.dumps(clip["retarget_report"], indent=2) + "\n"
    )
    del clip
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1200},
            record_video_dir="docs/evidence/video",
            record_video_size={"width": 1440, "height": 1200},
        )
        page = context.new_page()
        page.goto("http://127.0.0.1:8766")
        expect(page.locator("[data-action=train]")).to_be_enabled(timeout=30000)
        page.locator("[data-action=train]").click()
        deadline = time.monotonic() + 240
        shot = False
        while runtime.read().get("training", {}).get("completed_trials", 0) < 9:
            state = runtime.read()
            assert state["status"] != "error", runtime.error
            if time.monotonic() > deadline:
                raise RuntimeError("episode timeout")
            if (
                not shot
                and state.get("evidence", {}).get("changed_this_step", 0) > 0
                and state.get("sim_time", 0) > 0.5
            ):
                page.screenshot(path="docs/evidence/training-live.png", full_page=True)
                shot = True
            page.wait_for_timeout(300)
        page.locator("[data-action=stop]").click()
        expect(page.locator("#statusText")).to_have_text("listo", timeout=30000)
        page.screenshot(path="docs/evidence/training-results.png", full_page=True)
        state = runtime.read()
        (Path("docs/evidence") / "continuous-smoke.json").write_text(
            json.dumps(
                {
                    "root": str(root),
                    "training": state["training"],
                    "evidence": state["evidence"],
                    "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                },
                indent=2,
            )
            + "\n"
        )
        video = page.video
        context.close()
        video.save_as("docs/evidence/training-real.webm")
        browser.close()
    print(
        json.dumps(
            {
                "root": str(root),
                "completed": state["training"]["completed_trials"],
                "phase": state["training"]["phase"],
            }
        ),
        flush=True,
    )
finally:
    server.shutdown()
    server.server_close()
    runtime.close()
