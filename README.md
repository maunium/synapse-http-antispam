# synapse-http-antispam
A Synapse spam checker module that forwards requests to an HTTP server.

## Discussion
This project was written for use with Meowlnir, so it can be discussed in the
Meowlnir room: [#meowlnir:maunium.net](https://matrix.to/#/#meowlnir:maunium.net)

## Installation
In the Python environment where Synapse is installed:

```
pip install synapse-http-antispam
```

or if you want the main branch instead of the last release:

```
pip install synapse-http-antispam@git+https://github.com/maunium/synapse-http-antispam.git
```

### Installation with Synapse Debian packages
The upstream Debian packages for Synapse create a virtualenv in
`/opt/matrix-synapse`. You must install the module inside that virtualenv,
not globally on the system.

### Installation inside Docker
You can make your own overlay image to install the module:

```Dockerfile
FROM matrixdotorg/synapse

RUN pip install synapse-http-antispam
```

Alternatively, you can create a bind mount at runtime, e.g.

```
docker run -v /path/to/synapse_http_antispam.py:/usr/local/lib/python3.12/site-packages/synapse_http_antispam.py:ro ...
```

(you need to acquire `synapse_http_antispam.py` yourself and may need to adjust
the python version in the path)

## Configuration reference
The exact callbacks to enable depend on what you want to do with antispam.
Most users should not read these docs and should instead refer to the docs
of whatever antispam server they have. For example, if you want to block
invites, refer to the [Meowlnir] or [Draupnir] docs.

If you want to write your own antispam server or just want to find out all
available options, continue reading here.

[Meowlnir]: https://docs.mau.fi/meowlnir/invite-blocking.html
[Draupnir]: https://the-draupnir-project.github.io/draupnir-documentation/bot/synapse-http-antispam

Reference for the module configuration in `homeserver.yaml`:

```yaml
modules:
  - module: synapse_http_antispam.HTTPAntispam
    config:
      base_url: http://localhost:8080
      authorization: random string
      do_ping: true
      enabled_callbacks:
        - user_may_invite
      async:
        user_may_join_room: true
      fail_open:
        check_event_for_spam: true
```

If `enabled_callbacks` is not specified, all callbacks will be enabled.

See <https://element-hq.github.io/synapse/v1.126/modules/spam_checker_callbacks.html>
for the list of available callbacks. All callbacks except `check_media_file_for_spam`,
`check_registration_for_spam` and `should_drop_federated_event` are available.

The module will make HTTP requests to `<base_url>/<callback_name>` with all
function parameters as JSON fields. The `authorization` field will be sent as
a `Authorization: Bearer <value>` header if specified.

The response body must always be JSON. Any 2xx response will be return
`NOT_SPAM` to Synapse. The content of 2xx responses is ignored, so an empty
object is sufficient. Any other response is treated as a rejection and the
response body will be returned to the client as-is. If the `errcode` field is
not present in error responses, it will default to `M_FORBIDDEN`.

If the server returns a non-JSON response or if the request fails, the module
will fail closed and reject the callback with an `M_UNKNOWN` error by default,
except for callbacks specified in `fail_open`. Additionally, the `check_event_for_spam`
callback will fail open by default, unless set to `false` in `fail_open`.

Any callbacks set to `true` in the `async` map will be executed in the background
and will always return `NOT_SPAM` to Synapse. The response status and data will
be ignored for async callbacks.

if `do_ping` is set to `true`, the module will call the `ping` callback with an
`id` field, expecting a response with the same ID and `"status": "ok"`.
