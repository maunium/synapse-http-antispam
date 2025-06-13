import json
import logging
import random
import string

from synapse.api.errors import Codes, HttpResponseException
from synapse.events.utils import format_event_for_client_v2
from synapse.module_api import NOT_SPAM, EventBase, ModuleApi, SimpleHttpClient, UserProfile
from twisted.internet import defer

logger = logging.getLogger(__name__)


class HTTPAntispam:
    _http_client: SimpleHttpClient
    _url: str
    _headers: dict[str, list[str]]
    _fail_open: dict[str, bool]
    _async: dict[str, bool]

    def __init__(self, config: dict, api: ModuleApi) -> None:
        self._http_client = api.http_client
        self._url = config["base_url"]
        self._headers = {}
        if auth := config.get("authorization"):
            self._headers["Authorization"] = [f"Bearer {auth}"]
        elif auth_file := config.get("authorization_path"):
            with open(auth_file) as f:
                self._headers["Authorization"] = [f"Bearer {f.read().strip()}"]
        callbacks = {}
        all_callbacks = [x for x in dir(self) if not x.startswith("_")]
        enabled_callbacks = config.get("enabled_callbacks", all_callbacks)
        for callback in enabled_callbacks:
            callbacks[callback] = getattr(self, callback)
        self._fail_open = {
            # Soft failing all federated events would be a bad idea, so we fail open by default.
            # TODO it might be nice to allow federated events while failing local ones,
            #      so the error would be easier to notice.
            "check_event_for_spam": True,
            **config.get("fail_open", {}),
        }
        self._async = {
            **config.get("async", {}),
        }
        api.register_spam_checker_callbacks(**callbacks)
        if config.get("do_ping"):
            defer.ensureDeferred(self._do_ping(api))

    async def _do_ping(self, api: ModuleApi):
        url = f"{self._url}/ping"
        while True:
            try:
                req_id = "".join(random.choices(string.ascii_letters, k=8))
                resp = await self._http_client.post_json_get_json(
                    url, {"id": req_id}, self._headers
                )
                if resp.get("id") != req_id or resp.get("status") != "ok":
                    logger.error(
                        "Unexpected ping response from antispam server (POST %s with ID %s): %s",
                        url,
                        req_id,
                        resp,
                    )
                else:
                    logger.info("Successfully pinged antispam server with request ID %s", req_id)
                    return
            except Exception:
                logger.exception("Failed to ping antispam server (POST %s)", url)
            await api.sleep(5)

    async def _catch_errors(self, task: defer.Deferred, url: str):
        try:
            await task
        except Exception:
            logger.exception("Error in async callback (POST %s)", url)

    async def _do_request(self, path: str, data: dict):
        url = f"{self._url}/{path}"
        try:
            task = self._http_client.post_json_get_json(url, data, self._headers)
            if self._async.get(path, False):
                defer.ensureDeferred(self._catch_errors(task, url))
            else:
                await task
            return NOT_SPAM
        except HttpResponseException as e:
            try:
                data = json.loads(e.response)
            except Exception:
                logger.warning(
                    "Unexpected response from antispam server: %s (POST %s with %s)",
                    e.response,
                    url,
                    data,
                )
                if self._fail_open.get(path, False):
                    return NOT_SPAM
                return Codes.UNKNOWN, {"error": "Unexpected response from antispam server"}
            try:
                errcode = Codes(data["errcode"])
                data.pop("errcode")
                return errcode, data
            except (KeyError, ValueError):
                return Codes.FORBIDDEN, data
        except Exception:
            logger.exception("Failed to connect to antispam server (POST %s %s)", url, data)
            if self._fail_open.get(path, False):
                return NOT_SPAM
            return Codes.UNKNOWN, {"error": "Failed to connect to antispam server"}

    async def user_may_join_room(self, user: str, room: str, is_invited: bool):
        return await self._do_request(
            "user_may_join_room",
            {
                "user": user,
                "room": room,
                "is_invited": is_invited,
            },
        )

    async def accept_make_join(self, user: str, room: str):
        return await self._do_request(
            "accept_make_join",
            {
                "user": user,
                "room": room,
            },
        )

    async def user_may_invite(self, inviter: str, invitee: str, room_id: str):
        return await self._do_request(
            "user_may_invite",
            {
                "inviter": inviter,
                "invitee": invitee,
                "room_id": room_id,
            },
        )

    async def user_may_send_3pid_invite(
        self, inviter: str, medium: str, address: str, room_id: str
    ):
        return await self._do_request(
            "user_may_send_3pid_invite",
            {
                "inviter": inviter,
                "medium": medium,
                "address": address,
                "room_id": room_id,
            },
        )

    async def user_may_create_room(self, user_id: str):
        return await self._do_request(
            "user_may_create_room",
            {"user_id": user_id},
        )

    async def user_may_create_room_alias(self, user_id: str, room_alias: str):
        return await self._do_request(
            "user_may_create_room_alias",
            {"user_id": user_id, "room_alias": room_alias},
        )

    async def user_may_publish_room(self, user_id: str, room_id: str):
        return await self._do_request(
            "user_may_publish_room",
            {"user_id": user_id, "room_id": room_id},
        )

    async def check_username_for_spam(self, user_profile: UserProfile, requester_id: str):
        return await self._do_request(
            "check_username_for_spam",
            {
                "user_profile": user_profile,
                "requester_id": requester_id,
            },
        )

    async def check_login_for_spam(
        self,
        user_id: str,
        device_id: str | None,
        initial_display_name: str | None,
        request_info: list[tuple[str | None, str]],
        auth_provider_id: str | None = None,
    ):
        return await self._do_request(
            "check_login_for_spam",
            {
                "user_id": user_id,
                "device_id": device_id,
                "initial_display_name": initial_display_name,
                "request_info": request_info,
                "auth_provider_id": auth_provider_id,
            },
        )

    async def check_event_for_spam(self, event: EventBase):
        event_dict = format_event_for_client_v2(event.get_dict())
        event_dict["event_id"] = event.event_id
        return await self._do_request(
            "check_event_for_spam",
            {"event": event_dict},
        )

    async def federated_user_may_invite(self, event: EventBase):
        event_dict = format_event_for_client_v2(event.get_dict())
        event_dict["event_id"] = event.event_id
        return await self._do_request(
            "federated_user_may_invite",
            {"event": event_dict},
        )
