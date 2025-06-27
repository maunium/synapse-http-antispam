# v0.5.0 (2025-06-27)

* Added support for `federated_user_may_invite` callback introduced in Synapse
  1.134.0.
* Added option to ping antispam server on startup to make it easier to find
  error logs.

# v0.4.0 (2025-05-16)

* Improved installation and configuration instructions.
* Added support for `accept_make_join` callback for custom restricted join rules.
* Added support for loading the auth token from a file.

# v0.3.0 (2025-03-21)

* Added option to run callback requests asynchronously without blocking.
* Made HTTP failure behavior configurable for synchronous callbacks and changed
  `check_event_for_spam` to default to fail-open.

# v0.2.0 (2025-03-13)

* Added support for passing an authorization header to the webhook.
* Dropped support for `check_registration_for_spam` and `should_drop_federated_event`
  as they have different return formats than the other callbacks.
* Fixed field names to match Synapse docs

# v0.1.0 (2025-03-09)

Initial release.
