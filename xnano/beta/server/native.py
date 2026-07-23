"""xnano.beta.server.native

---

Render beta applications offscreen and expose their cell frames to browsers.
"""

from __future__ import annotations

import html
import json
import urllib.parse
from typing import Any, Callable

from xnano.beta.core.runtime import Runtime
from xnano.beta.server.requests import RequestServer, _RequestHandler

_CLIENT_HTML = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
html,body{{height:100%;margin:0;background:#0b0d10;color:#f5f7fa}}
pre{{box-sizing:border-box;margin:0;min-height:100%;padding:1rem;
font:16px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;white-space:pre}}
</style>
<pre id="screen" aria-live="polite"></pre>
<script>
const screen=document.querySelector("#screen");
function send(event){{
  fetch("/xnano/event",{{method:"POST",headers:{{"content-type":"application/json"}},
    body:JSON.stringify(event)}});
}}
document.addEventListener("keydown",event=>{{
  const modifiers=[];
  if(event.ctrlKey) modifiers.push("ctrl");
  if(event.altKey) modifiers.push("alt");
  if(event.shiftKey) modifiers.push("shift");
  const names={{Escape:"esc",Enter:"enter",ArrowUp:"up",ArrowDown:"down",
    ArrowLeft:"left",ArrowRight:"right"," ":"space"}};
  modifiers.push(names[event.key]||event.key.toLowerCase());
  send({{type:"keyboard",binding:modifiers.join("+"),kind:"press",
    character:event.key.length===1?event.key:null}});
}});
screen.addEventListener("mousedown",event=>{{
  const box=screen.getBoundingClientRect();
  const style=getComputedStyle(screen);
  const width=parseFloat(style.fontSize)*0.6;
  const height=parseFloat(style.lineHeight);
  send({{type:"mouse",kind:"press",button:["left","middle","right"][event.button],
    x:Math.max(0,Math.floor((event.clientX-box.left)/width)),
    y:Math.max(0,Math.floor((event.clientY-box.top)/height))}});
}});
async function paint(){{
  const response=await fetch("/xnano/frame",{{cache:"no-store"}});
  const frame=await response.json();
  screen.textContent=frame.text;
  document.title=frame.title||{title_json};
}}
paint(); setInterval(paint,50);
</script>"""


class NativeWebServer(RequestServer):
    """Serve one application from an owned offscreen runtime.

    Attributes:
        factory: Callable that creates the root grid or component.
        root: Root grid or component being served.
        title: Browser document title.
        runtime: Offscreen runtime used to render frames and dispatch input.

    Example:
        >>> from xnano.beta.components import Text
        >>> server = NativeWebServer(("127.0.0.1", 0), lambda: Text("Ready"))
        >>> server.server_address[1] > 0
        True
        >>> server.server_close()
    """

    runtime: Runtime[Any]

    def __init__(
        self,
        address: tuple[str, int],
        factory: Callable[[], Any],
        *,
        state: Any = None,
        title: str = "xnano",
        width: int = 80,
        height: int = 24,
    ) -> None:
        self.factory = factory
        self.root = factory()
        self.title = title
        self.runtime = Runtime.offscreen(
            width,
            height,
            state=state,
            title=title,
        )
        self.runtime.set_root(self.root)
        super().__init__(address, self.root, runtime=self.runtime)
        self.RequestHandlerClass = _NativeWebHandler

    def server_close(self) -> None:
        """Close both the HTTP listener and offscreen runtime."""
        self.runtime.close()
        super().server_close()


class _NativeWebHandler(_RequestHandler):
    """Serve the browser shell, frame endpoint, and request hooks."""

    server: NativeWebServer

    def do_GET(self) -> None:
        """Serve the browser shell, a frame, or a declared GET route."""
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/":
            title = html.escape(self.server.title)
            payload = _CLIENT_HTML.format(
                title=title,
                title_json=json.dumps(self.server.title),
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if parsed.path == "/xnano/frame":
            frame = self.server.runtime.render()
            payload = json.dumps(
                {
                    "text": frame.text,
                    "ansi": frame.ansi,
                    "width": frame.width,
                    "height": frame.height,
                    "title": frame.title,
                    "revision": frame.revision,
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self._dispatch_request()

    def do_POST(self) -> None:
        """Dispatch browser input or a declared POST route."""
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path != "/xnano/event":
            self._dispatch_request()
            return
        try:
            length = int(self.headers.get("content-length", "0"))
            if length < 1 or length > 65_536:
                raise ValueError
            data = json.loads(self.rfile.read(length))
            event = _browser_event(data)
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            self.send_error(400, "Invalid browser event")
            return
        self.server.runtime.dispatch(event)
        self.send_response(204)
        self.end_headers()


def _browser_event(data: dict[str, Any]) -> Any:
    """Build a public beta event from validated browser data."""
    from xnano.beta.events import (
        Event,
        KeyboardEventData,
        MouseEventData,
    )

    if data["type"] == "keyboard":
        binding = str(data["binding"])
        if not binding or len(binding) > 100:
            raise ValueError
        event_data = KeyboardEventData.from_binding(
            binding,
            kind=data.get("kind", "press"),
            character=data.get("character"),
        )
    elif data["type"] == "mouse":
        event_data = MouseEventData(
            kind=data["kind"],
            x=max(0, int(data["x"])),
            y=max(0, int(data["y"])),
            button=data.get("button", "unknown"),
        )
    else:
        raise ValueError
    return Event.from_data(event_data)


def serve_native(
    factory: Callable[[], Any],
    *,
    state: Any = None,
    title: str = "xnano",
    host: str = "127.0.0.1",
    port: int = 8000,
    width: int = 80,
    height: int = 24,
) -> None:
    """Serve a beta application until interrupted.

    Args:
        factory: Callable returning the root grid or component.
        state: Application state shared with hooks.
        title: Browser document title.
        host: Bind address.
        port: Bind port.
        width: Offscreen viewport width.
        height: Offscreen viewport height.
    """
    server = NativeWebServer(
        (host, port),
        factory,
        state=state,
        title=title,
        width=width,
        height=height,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


__all__ = ("NativeWebServer", "serve_native")
