# Architecture

The skill is a portable set of agent instructions. Business context belongs to each project, outside the skill and outside public version control.

## Data flow

1. The owner supplies brand context and approves a profile shortlist.
2. `setup_project.py` validates local JSON configuration and creates a new project atomically, without replacing existing data or enabling a scheduler.
3. The agent collects through its permitted Instagram or TikTok source. One project contains one platform to keep native post and audio identifiers unambiguous.
4. `update_registry.py` applies subsequent account decisions under a write lock; omitted profiles are disabled, historical posts and observations stay intact, and the queue excludes unapproved profiles.
5. Verified batches enter `trendwatch_data.py`. State stores approved profiles, post metadata, append-preserved observations, audio observations and attempts. The project timezone defines calendar-day deduplication; publication time defines the first 168 hours.
6. Render produces JSON and an HTML report using that project's name and configured report language (Russian or English labels, English fallback). The agent adds coverage, execution status, analysis and production briefs using that project's goal, products, resources and language.
7. A separately authorized scheduler can invoke the agent with `AUTOMATION_PROMPT.md`. Configuration does not execute schedules.

## Ownership and boundaries

- `skill/`: generic methodology, templates and standalone local Python tools. Copy this directory into a supported skill location named `trendwatch`.
- `templates/`: blank private-input starters; account approval is never inherited.
- `project.json` and `brief.md`: brand goal, platform, timezone, audience, products, constraints, desired language and optional heuristics. `state.json` is the operational approved registry after initialization.
- `helpers/`: optional Instagram evidence adapters. They do not provide browser access. Finalization requires a finished run with an explicit status; report labels remain Russian.
- Browser and scheduler: supplied by the host environment and independently verified. Python helpers perform no network calls and read no account credentials.

Low-level init defaults to UTC if called directly; the recommended setup requires an explicit timezone. Existing projects retain their stored timezone. Numeric heuristics are empty by default and do not change measured metrics.

The public repository excludes brand inputs, observations, media, browser evidence and secrets through its ignore rules and pre-publication review. Existing local brand deployments and schedules are separate consumers and are not changed by this repository update.
