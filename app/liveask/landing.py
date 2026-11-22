"""The landing page's two forms, as plain HTML form posts that work without JavaScript.

POST /create   a room title in a form body -> 303 to the host page, token in the #fragment
GET  /join     ?code=ABC234 -> 303 to the audience page; a malformed code goes back to the form

Both answer with a redirect, never a page, so the browser lands on the real page and the
back button does not resubmit the form.
"""

from __future__ import annotations

from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from pydantic import ValidationError

from liveask import ratelimit, rooms
from liveask.common import CODE_RE, Pool

router = APIRouter(include_in_schema=False)

MAX_FORM_BYTES = 4096


def see_other(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)  # 303: the browser follows with GET


@router.post("/create")
async def create_from_form(request: Request, pool: Pool) -> Response:
    if not request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
        return see_other("/#create")
    body = await request.body()
    if len(body) > MAX_FORM_BYTES:
        return see_other("/#create")
    fields = parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True)
    try:
        data = rooms.RoomIn(title=(fields.get("title") or [""])[0])
    except ValidationError:
        return see_other("/#create")  # the page's own check explains what to fix
    wait = ratelimit.room_creation_retry_after(request)
    if wait:  # a plain form post has no page to show an error on, so answer with a short text
        return PlainTextResponse(
            f"Too many rooms were created from your network. Try again in {wait} seconds.",
            status_code=429,
            headers={"Retry-After": str(wait)},
        )
    room = await rooms.create_room_record(pool, data.title)
    return see_other(room["host_url"])


@router.get("/join")
async def join(code: str = "") -> RedirectResponse:
    code = code.strip().upper()
    return see_other(f"/r/{code}" if CODE_RE.match(code) else "/#join")
