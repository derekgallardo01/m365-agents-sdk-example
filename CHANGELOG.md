# Changelog

Notable changes to the M365 Agents SDK example. Dates are when the
change landed on `main`.

## 2026-06-28 — Initial public release (v1.0.0)
- `manifest.py` — declarative channels + intents + connectors with
  static `validate()` (the SDK's deploy-time check)
- `handlers.py` — 5 typed intent handlers + registry, plus an
  unmatched-fallback
- `connectors.py` — mocked `graph_calendar` / `graph_directory` /
  `graph_reports` / `sharepoint_search` with realistic Graph shapes
- `agent.py` — message-pump loop, `_dispatch` provider seam (stub-
  by-default, one method swap to wire the real SDK), channel-aware
  `_render` (chat / email / adaptive_card), per-user-per-channel
  conversation log
- `cli.py` — scripted demo, `--interactive` REPL with `channel ...`
  switching mid-conversation, `--validate-manifest` static check,
  `--json` for machine-readable transcripts
- 25 unit tests (8 manifest + 9 handlers + 8 agent loop)
- 6 golden eval cases, CI gates on 100% pass
- CI on Python 3.10/3.11/3.12 (validate-manifest + pytest + evals +
  scripted demo smoke)
- `pyproject.toml` with `[m365]` optional extra for
  `botbuilder-core`
- Docs trio: `getting-started`, `architecture`, `customization`,
  `evaluation`, `diagrams`, `faq`, plus `examples/manifest-walkthrough.md`
- OSS niceties: `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`,
  `CITATION.cff`, `.editorconfig`, `.devcontainer/devcontainer.json`,
  `.github/ISSUE_TEMPLATE/*`, `.github/PULL_REQUEST_TEMPLATE.md`,
  `.github/dependabot.yml`
- `Dockerfile`, `pages.yml` (live demo across 3 channel cards),
  `screenshots.yml`, `portfolio.yml`
- README badges: CI + License (MIT) + Python (3.10+) + Open in
  Codespaces
- Theme: Microsoft blue
