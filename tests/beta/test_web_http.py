"""HTTP integration tests against the live Starlette app via httpx.

These exercise the full ASGI stack — routing, cookies, htmx headers, and
HTML responses — using ``httpx.ASGITransport`` so every call is a real
request/response through ``Web.build_app``.
"""

from __future__ import annotations

import re
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import httpx
import pytest

from tests.beta.grids import (
    ClickableGrid,
    InteractiveGrid,
    RequestHookGrid,
)
from xnano.beta.web import Web


@asynccontextmanager
async def asgi_client(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    """httpx async client bound to ``app`` over ASGI transport."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


def _click_target_id(html: str) -> str:
    """Extract the first ``/xnano/click/{id}`` target from rendered HTML."""
    match = re.search(r"/xnano/click/(t\d+)", html)
    assert match is not None, f"no click target in: {html[:200]}"
    return match.group(1)


def _input_target_id(html: str) -> str:
    """Extract the first ``/xnano/input/{id}`` target from rendered HTML."""
    match = re.search(r"/xnano/input/(i\d+)", html)
    assert match is not None, f"no input target in: {html[:200]}"
    return match.group(1)


# ── page + built-in routes ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_index_returns_full_document() -> None:
    """GET / returns a full HTML page with shell assets and grid content."""
    grid = ClickableGrid()
    app = Web(title="clickable").build_app(grid)
    async with asgi_client(app) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        body = response.text
        assert "<!doctype html>" in body.lower()
        assert "cdn.tailwindcss.com" in body
        assert "htmx.org" in body
        assert 'id="xnano-app"' in body
        assert "Click me" in body
        assert "Count: 0" in body
        assert grid.count == 0


@pytest.mark.asyncio
async def test_post_click_route_mutates_and_returns_fragment() -> None:
    """POST /xnano/click/{id} fires @on_click and returns a fragment."""
    grid = ClickableGrid()
    app = Web(title="clickable").build_app(grid)
    async with asgi_client(app) as client:
        index = await client.get("/")
        target_id = _click_target_id(index.text)

        response = await client.post(f"/xnano/click/{target_id}")
        assert response.status_code == 200
        assert grid.count == 1
        assert "Count: 1" in response.text
        assert "<!doctype html>" not in response.text.lower()

        again = await client.post(f"/xnano/click/{target_id}")
        assert grid.count == 2
        assert "Count: 2" in again.text


@pytest.mark.asyncio
async def test_post_key_route_matches_keyboard_binding() -> None:
    """POST /xnano/key?binding=… dispatches @on_keyboard handlers."""
    grid = InteractiveGrid()
    app = Web().build_app(grid)
    async with asgi_client(app) as client:
        await client.get("/")
        response = await client.post("/xnano/key", params={"binding": "up"})
        assert response.status_code == 200
        assert grid.count == 10
        assert "Count: 10" in response.text

        response = await client.post(
            "/xnano/key", params={"binding": "ctrl+k"}
        )
        assert grid.count == 20
        assert "Count: 20" in response.text

        response = await client.post("/xnano/key", params={"binding": "x"})
        assert grid.count == 20
        assert "Count: 20" in response.text


@pytest.mark.asyncio
async def test_post_input_route_syncs_text_content() -> None:
    """POST /xnano/input/{id} writes form value onto the Text field."""
    grid = InteractiveGrid()
    app = Web().build_app(grid)
    async with asgi_client(app) as client:
        index = await client.get("/")
        target_id = _input_target_id(index.text)

        response = await client.post(
            f"/xnano/input/{target_id}",
            data={"value": "hammad"},
        )
        assert response.status_code == 204
        assert grid.name.content == "hammad"
        assert grid.name.cursor == len("hammad")

        refreshed = await client.get("/")
        assert 'value="hammad"' in refreshed.text


@pytest.mark.asyncio
async def test_post_tick_route_advances_interval_hooks() -> None:
    """POST /xnano/tick pumps interval-gated @on_tick handlers."""
    grid = InteractiveGrid()
    app = Web().build_app(grid)
    async with asgi_client(app) as client:
        await client.get("/")
        first = await client.post("/xnano/tick")
        assert first.status_code == 200
        ticks_after_first = grid.ticks
        assert ticks_after_first >= 1

        await client.post("/xnano/tick")
        assert grid.ticks == ticks_after_first

        time.sleep(0.06)
        await client.post("/xnano/tick")
        assert grid.ticks == ticks_after_first + 1


# ── @on_get_request / @on_post_request HTTP routes ────────────────────


@pytest.mark.asyncio
async def test_post_increment_htmx_fragment_and_state() -> None:
    """POST /increment via htmx mutates state and returns a fragment."""
    grid = RequestHookGrid()
    app = Web(title="request hooks").build_app(grid)
    async with asgi_client(app) as client:
        response = await client.post(
            "/increment",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 200
        assert grid.count == 1
        assert "Count: 1" in response.text
        assert "<!doctype html>" not in response.text.lower()
        assert "cdn.tailwindcss.com" not in response.text

        again = await client.post(
            "/increment",
            headers={"HX-Request": "true"},
        )
        assert grid.count == 2
        assert "Count: 2" in again.text
        assert grid.note == "double"
        assert "double" in again.text


@pytest.mark.asyncio
async def test_get_status_full_page_vs_htmx_fragment() -> None:
    """Same @on_get_request path: full page for browsers, fragment for htmx."""
    grid = RequestHookGrid()
    app = Web(title="request hooks").build_app(grid)
    async with asgi_client(app) as client:
        await client.post("/increment", headers={"HX-Request": "true"})
        await client.post("/increment", headers={"HX-Request": "true"})
        assert grid.count == 2

        browser = await client.get("/status")
        assert browser.status_code == 200
        assert "status:2" in browser.text
        assert "<!doctype html>" in browser.text.lower()
        assert 'id="xnano-app"' in browser.text
        assert "cdn.tailwindcss.com" in browser.text

        htmx = await client.get("/status", headers={"HX-Request": "true"})
        assert htmx.status_code == 200
        assert "status:2" in htmx.text
        assert "<!doctype html>" not in htmx.text.lower()
        assert "cdn.tailwindcss.com" not in htmx.text


@pytest.mark.asyncio
async def test_get_index_runs_root_on_get_each_visit() -> None:
    """Each GET / increments the @on_get_request('/') visit counter."""
    grid = RequestHookGrid()
    app = Web(title="request hooks").build_app(grid)
    async with asgi_client(app) as client:
        first = await client.get("/")
        second = await client.get("/")
        assert first.status_code == 200
        assert second.status_code == 200
        assert grid.visits == 2


@pytest.mark.asyncio
async def test_unknown_route_returns_404() -> None:
    """Paths not registered by the app return 404 and leave state alone."""
    grid = RequestHookGrid()
    app = Web(title="request hooks").build_app(grid)
    async with asgi_client(app) as client:
        await client.post("/increment", headers={"HX-Request": "true"})
        assert grid.count == 1

        response = await client.post("/nope")
        assert response.status_code == 404
        assert grid.count == 1


@pytest.mark.asyncio
async def test_wrong_method_on_request_hook_path() -> None:
    """GET on a POST-only @on_post_request path does not fire the POST handler."""
    grid = RequestHookGrid()
    app = Web(title="request hooks").build_app(grid)
    async with asgi_client(app) as client:
        response = await client.get("/increment")
        # Route exists for POST only → Method Not Allowed.
        assert response.status_code == 405
        assert grid.count == 0


# ── factory / cookie sessions over HTTP ───────────────────────────────


@pytest.mark.asyncio
async def test_factory_mode_isolates_sessions_via_cookies() -> None:
    """Two visitors with different cookies keep independent grid state."""
    app = Web(title="factory").build_app(RequestHookGrid)

    async with asgi_client(app) as client_a:
        first = await client_a.get("/")
        assert first.status_code == 200
        cookie_a = client_a.cookies.get("xnano-session")
        assert cookie_a is not None

        await client_a.post(
            "/increment",
            headers={"HX-Request": "true"},
        )
        await client_a.post(
            "/increment",
            headers={"HX-Request": "true"},
        )
        status_a = await client_a.get("/status")
        assert "status:2" in status_a.text

    # Visitor B on a fresh client so cookies are not shared.
    async with asgi_client(app) as client_b:
        first_b = await client_b.get("/")
        cookie_b = client_b.cookies.get("xnano-session")
        assert cookie_b is not None
        assert cookie_b != cookie_a

        status_b = await client_b.get("/status")
        assert "status:0" in status_b.text

        await client_b.post(
            "/increment",
            headers={"HX-Request": "true"},
        )
        status_b = await client_b.get("/status")
        assert "status:1" in status_b.text

    # A is unchanged (resume with the original session cookie).
    # httpx stores ASGI cookies under the ``testserver.local`` domain —
    # set the value without a domain so it is sent on the next request.
    async with asgi_client(app) as client_resume:
        client_resume.cookies.set("xnano-session", cookie_a)
        status_a = await client_resume.get("/status")
        assert "status:2" in status_a.text


@pytest.mark.asyncio
async def test_factory_mode_reuses_session_cookie() -> None:
    """Returning with the same cookie continues the same session state."""
    app = Web(title="factory").build_app(RequestHookGrid)
    async with asgi_client(app) as client:
        first = await client.get("/")
        session_id = client.cookies.get("xnano-session")
        assert session_id
        assert first.cookies.get("xnano-session") == session_id

        await client.post(
            "/increment",
            headers={"HX-Request": "true"},
        )

        again = await client.get("/status")
        assert "status:1" in again.text
        assert client.cookies.get("xnano-session") == session_id
