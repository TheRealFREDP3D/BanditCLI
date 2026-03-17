# Changelog

All notable changes to BanditCLI are documented here.

---

## [0.3.0] - 2026-03-17

### Added
- **Automatic password detection** — terminal output is continuously scanned for
  32-character Bandit-style passwords using a regex with a sliding-window buffer
  to handle passwords split across SSH data chunks.
- **LevelCompleteModal** — when a password is detected a congratulatory modal
  appears showing the recovered password and offering a one-click
  "Login to Level N →" button.
- **Auto-login to next level** — clicking the button disconnects the current
  SSH session, pre-fills the username (`banditN`) and password fields, and
  reconnects automatically.
- **`Session.recovered_passwords`** — new `dict[int, str]` field on `Session`
  that persists recovered passwords to disk alongside the rest of session state.
- **`Session.store_password()`** and **`Session.get_password_for_level()`**
  helper methods.
- **`SessionManager.store_recovered_password()`** — thread-safe method to save
  a discovered password and flush to disk atomically.
- **`PasswordDetector`** class in `main.py` — responsible for scanning chunks,
  deduplicating candidates, and enforcing a cooldown between successive triggers.
- Level is marked complete (`Session.mark_level_complete()`) as soon as a
  password is detected; progress is force-saved immediately.

### Changed
- `Session.get_progress_summary()` now includes `passwords_recovered` count.
- `PasswordDetector` is reset whenever the SSH connection state changes to
  prevent stale detections across reconnects.
- `_level_complete_modal_open` guard prevents stacking multiple modals when
  rapid successive detections occur.

---

## [0.2.2] - prior

- See git history for earlier changes.