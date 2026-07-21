"""
Budget Playground reverse proxy — injects a /bp-api/* route into Streamlit's
running Tornado server so that browser-side JS inside the iframe can reach the
Budget Playground Node.js API (port 5002) via same-origin requests (port 5000).

How it works
------------
Replit only exposes port 5000 to the outside world. All other ports (5002,
etc.) are only reachable inside the container. Browser JS in iframes therefore
cannot call http://localhost:5002 directly. Instead the HTML uses a relative
path /bp-api/* which hits the Streamlit server. This module adds a Tornado
RequestHandler at that path that proxies the request server-side to port 5002.

Finding the Tornado Application
--------------------------------
Streamlit does not expose its internal Tornado Application object publicly.
We use Python's gc module to locate the first tornado.web.Application instance
in memory — this is always Streamlit's application because it is the only
Tornado app in the process. We then call add_handlers() on it to register our
routes. If no Application is found (e.g. running in a test without Streamlit),
the function is a silent no-op.

This is called once per process lifetime; a module-level flag prevents
duplicate route registration across Streamlit reruns.
"""

from __future__ import annotations
import asyncio
import gc
import logging
from http.client import HTTPConnection

import tornado.web

log = logging.getLogger(__name__)

_PROXY_INSTALLED = False


class _BPProxyHandler(tornado.web.RequestHandler):
    """
    Transparent HTTP proxy for /bp-api/* → localhost:5002/*.

    Uses stdlib http.client (synchronous) run via asyncio's thread executor so
    it does not block the IOLoop. All HTTP methods are forwarded verbatim.

    Tornado passes the regex capture group from r"/bp-api/(.*)" as a positional
    argument; all handler methods accept *args to absorb that argument.
    """

    SUPPORTED_METHODS = ("GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH")

    async def _forward(self) -> None:
        path = self.request.uri  # includes query string, e.g. /bp-api/api/budget-playground/accounts
        if path.startswith("/bp-api"):
            path = path[len("/bp-api"):]
        if not path:
            path = "/"

        method  = self.request.method
        body    = self.request.body or None
        headers = {
            k: v for k, v in self.request.headers.get_all()
            if k.lower() not in ("host", "connection", "transfer-encoding")
        }
        headers["Host"] = "localhost:5002"

        def _do_request():
            conn = HTTPConnection("localhost", 5002, timeout=30)
            try:
                conn.request(method, path, body=body, headers=headers)
                resp = conn.getresponse()
                return resp.status, resp.getheaders(), resp.read()
            finally:
                conn.close()

        try:
            loop = asyncio.get_event_loop()
            status, resp_headers, resp_body = await loop.run_in_executor(None, _do_request)
        except Exception as exc:
            log.warning("bp-proxy: upstream error: %s", exc)
            self.set_status(502)
            self.set_header("Content-Type", "application/json")
            self.finish(f'{{"error":"upstream unavailable: {exc}"}}')
            return

        self.set_status(status)
        skip = {"content-encoding", "transfer-encoding", "connection", "content-length"}
        for name, value in resp_headers:
            if name.lower() not in skip:
                self.set_header(name, value)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS,PATCH")
        self.set_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.finish(resp_body)

    # *args absorbs Tornado's regex capture group from r"/bp-api/(.*)"
    async def get(self, *args):     await self._forward()
    async def post(self, *args):    await self._forward()
    async def put(self, *args):     await self._forward()
    async def delete(self, *args):  await self._forward()
    async def patch(self, *args):   await self._forward()
    async def options(self, *args): await self._forward()


def install_proxy() -> bool:
    """
    Find Streamlit's Tornado Application in memory and register /bp-api/* routes.
    Safe to call multiple times — routes are only registered once.
    Returns True if installation succeeded, False otherwise.
    """
    global _PROXY_INSTALLED
    if _PROXY_INSTALLED:
        return True

    try:
        tornado_app: tornado.web.Application | None = None
        for obj in gc.get_objects():
            try:
                if isinstance(obj, tornado.web.Application) and hasattr(obj, "add_handlers"):
                    tornado_app = obj
                    break
            except Exception:
                continue

        if tornado_app is None:
            log.debug("bp-proxy: no Tornado Application found in gc; skipping proxy install")
            return False

        tornado_app.add_handlers(
            r".*",
            [(r"/bp-api/(.*)", _BPProxyHandler)],
        )
        _PROXY_INSTALLED = True
        log.info("bp-proxy: /bp-api/* proxy installed successfully")
        return True

    except Exception as exc:
        log.warning("bp-proxy: failed to install proxy: %s", exc)
        return False
