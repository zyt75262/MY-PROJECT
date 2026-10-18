# SilverBridge English Edition - Validation

Version 1.5.0-en, 2026-10-18.

- 12 Python tests passed, covering app behavior, API, database isolation and selective import.
- JavaScript syntax and stub-DOM rendering checks passed. Initial built-in visible interface text is checked for untranslated Chinese text. User-generated text deliberately retains its original language.
- Both real command-line programs started simultaneously on default ports 8765 and 8766 using separate databases. Their APIs and database schemas remain separate.
- Stopping one left the other working; saved requests and replies survived a restart.
- Import copied only the relevant app tables, rejected a populated target and left the source database unchanged.

A browser executable was unavailable in this environment. These checks are not visual browser QA or acceptance testing on two physical devices. No public deployment was performed.
