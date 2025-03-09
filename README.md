# synapse-http-antispam
A Synapse spam checker module that forwards requests to an HTTP server.

## Installation
```
pip install synapse-http-antispam
```

or

```
pip install git+https://github.com/maunium/synapse-http-antispam#egg=synapse-http-antispam
```

## Configuration
Add the following to your `homeserver.yaml`:

```yaml
modules:
  - module: synapse_http_antispam.HTTPAntispam
    config:
      base_url: http://localhost:8080
      enabled_callbacks:
        - user_may_invite
```

If `enabled_callbacks` is not specified, all callbacks will be enabled.

See <https://element-hq.github.io/synapse/v1.126/modules/spam_checker_callbacks.html>
for the list of available callbacks. All callbacks except `check_media_file_for_spam` are available.

The module will make HTTP requests to `<base_url>/<callback_name>` with all function parameters as JSON fields.

Any 2xx response will be return `NOT_SPAM` to Synapse and the response body will be ignored.

Any other response is treated as a rejection. The response body must be JSON and will be returned to the client as is.
If the `errcode` field is not present, it will default to `M_FORBIDDEN`.

If the server returns a non-JSON response or if the request fails, the module will fail closed and reject the callback
with an `M_UNKNOWN` error.
