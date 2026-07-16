"""Single source of truth for the app's version, used by the auto-update
check. Bump this on any release that should trigger an update prompt --
the update-check endpoint compares this value against the same file's
contents on the GitHub repo's main branch."""
APP_VERSION = "2.0.0"
