# unreleased

* Made HTTP failure behavior configurable and changed `check_event_for_spam` to
  default to fail-open.

# v0.2.0 (2025-03-13)

* Added support for passing an authorization header to the webhook.
* Dropped support for `check_registration_for_spam` and `should_drop_federated_event`
  as they have different return formats than the other callbacks.
* Fixed field names to match Synapse docs

# v0.1.0 (2025-03-09)

Initial release.
