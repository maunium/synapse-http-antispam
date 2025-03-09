from synapse.module_api import (
    ModuleApi,
    NOT_SPAM,
    SimpleHttpClient,
    UserProfile,
    EventBase,
)
from synapse.api.errors import Codes, HttpResponseException
from synapse.events.utils import format_event_for_client_v2
import json
import logging

logger = logging.getLogger(__name__)


class HTTPAntispam:
    _http_client: SimpleHttpClient
    _url: str

    def __init__(self, config: dict, api: ModuleApi) -> None:
        self._http_client = api.http_client
        self._url = config["base_url"]
        callbacks = {}
        all_callbacks = [x for x in dir(self) if not x.startswith("_")]
        enabled_callbacks = config.get("enabled_callbacks", all_callbacks)
        for callback in enabled_callbacks:
            callbacks[callback] = getattr(self, callback)
        api.register_spam_checker_callbacks(**callbacks)

    async def _do_request(self, path: str, data: dict):
        url = f"{self._url}/{path}"
        try:
            await self._http_client.post_json_get_json(url, data)
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
                return Codes.UNKNOWN, {
                    "error": "Unexpected response from antispam server"
                }
            try:
                errcode = Codes(data["errcode"])
                data.pop("errcode")
                return errcode, data
            except (KeyError, ValueError):
                return Codes.FORBIDDEN, data
        except Exception:
            logger.exception(
                "Failed to connect to antispam server (POST %s %s)", url, data
            )
            return Codes.UNKNOWN, {"error": "Failed to connect to antispam server"}

    async def user_may_join_room(self, user_id: str, room_id: str, is_invited: bool):
        return await self._do_request(
            "user_may_join_room",
            {
                "user_id": user_id,
                "room_id": room_id,
                "is_invited": is_invited,
            },
        )

    async def user_may_invite(self, user_id: str, room_id: str, inviter_user_id: str):
        return await self._do_request(
            "user_may_invite",
            {
                "user_id": user_id,
                "room_id": room_id,
                "inviter_user_id": inviter_user_id,
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

    async def check_username_for_spam(
        self, user_profile: UserProfile, requester_id: str
    ):
        return await self._do_request(
            "check_username_for_spam",
            {
                "user_profile": user_profile,
                "requester_id": requester_id,
            },
        )

    async def check_registration_for_spam(
        self,
        email_threepid: dict | None,
        username: str | None,
        request_info: list[tuple[str, str]],
        auth_provider_id: str | None = None,
    ):
        return await self._do_request(
            "check_registration_for_spam",
            {
                "email_threepid": email_threepid,
                "username": username,
                "request_info": request_info,
                "auth_provider_id": auth_provider_id,
            },
        )

    async def check_login_for_spam(
        self,
        user_id: str,
        device_id: str,
        initial_display_name: str,
        request_info: list[tuple[str, str]],
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

    async def should_drop_federated_event(self, event: EventBase):
        event_dict = format_event_for_client_v2(event.get_dict())
        event_dict["event_id"] = event.event_id
        return await self._do_request(
            "should_drop_federated_event",
            {"event": event_dict},
        )
