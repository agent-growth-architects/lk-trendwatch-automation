# Set up a brand project

Use this reference for a new brand or a new monitoring platform. Reuse an existing brief, approvals and project files when they cover the request; ask only for missing choices that affect the work.

## Minimal brief

Capture the brand and its product or service; audience, geography and language; goal/KPI and traffic path; requested platform; inventory, availability or service capacity; production team, time, budget and other constraints; prior own-account tests; requested output and how the team will use it. Record unknowns as unknown. A local setup requires a nonempty brand name and goal, one platform (`instagram` or `tiktok`), and an explicit IANA timezone such as `Europe/London`. Do not infer timezone from the agent's machine, language or an old project.

Use one monitoring directory per brand and platform. A brand researching both platforms gets two monitoring projects and separately labeled evidence. The data helper uses post/audio IDs within a project; do not mix cross-platform IDs in the same state.

## Propose accounts, then record approval

Build a shortlist appropriate to the goal, category, market and available review time. There is no fixed account count or mandatory list. Balance relevant direct, adjacent, creative-reference, partner and own accounts where useful; explain each inclusion. Verify exact handles and profile URLs against source evidence, keep unresolved identities visible, and do not substitute namesakes.

The registry input is a JSON list. Each entry carries an explicit boolean `approved`; proposals start with `false`. Record the user's account-selection decision before setting it to `true`. Approval and identity verification are separate: live collection needs both an approved profile and a real verified handle. An empty registry is valid for setup while the shortlist is pending. Repository fixture/sample names and handles are examples, not verified or approved live targets.

Useful registry fields are `name`, `handle`, `platform`, `profile_url`, `verification_source`, `role`, `inclusion_reason`, `status` and `approved`. Use handles without `@` or a URL. Approved entries with handles require `verification_source` and `inclusion_reason`; these fields record evidence supplied by the agent, not automated platform verification. Each entry must match the project's single platform. Keep verification evidence and the approval decision in project notes; a boolean alone is not an identity check.

## Initialize local files

Run from the skill folder, or resolve `scripts/` relative to the real `SKILL.md` location. Keep the project and JSON inputs outside the installed skill. The complete skill folder can be copied with its `references/`, `assets/` and `scripts/`; no previous owner's workspace is required.

Prepare `BRAND_JSON` using this structure, replacing the example brand, goal and timezone with the actual brief:

```json
{
  "name": "Example service brand",
  "platform": "instagram",
  "timezone": "Europe/London",
  "audience": "Record audience and geography from the brief",
  "goal": "Identify feasible video tests for qualified service enquiries",
  "language": "English",
  "products": ["Describe the actual product or service"],
  "constraints": ["Record available people, inventory/capacity and production time"],
  "schedule": {"enabled": false, "local_time": null},
  "heuristics": []
}
```

Then run:

```bash
python3 scripts/setup_project.py --project PROJECT --config BRAND_JSON --registry REGISTRY_JSON
python3 scripts/trendwatch_data.py queue --project PROJECT --output QUEUE_JSON
python3 scripts/trendwatch_data.py validate --project PROJECT
```

Setup creates `project.json`, `brief.md`, `registry.json`, `state.json`, `daily-report.html` and `daily-summary.json`. It requires a new project directory and refuses to overwrite an existing one; reuse an existing project through the data commands instead of running setup over it. Read back the created brief/configuration, timezone and registry. Check that the discovery queue reflects only approved entries with handles. A valid empty project confirms setup, not source access or monitoring success. Use [data-and-snapshots.md](data-and-snapshots.md) for ingestion and observation semantics, and the selected platform reference for the access preflight. Helpers persist supplied evidence; they do not collect from a platform or authenticate automatically.

## Apply account decisions after setup

After checking identities and obtaining the required account approval, apply the local registry to an existing project:

```bash
python3 scripts/update_registry.py --project PROJECT --registry REGISTRY_JSON
python3 scripts/trendwatch_data.py queue --project PROJECT --output QUEUE_JSON
```

The update preserves posts and observations. Profiles omitted from the new list remain in state with approval disabled and leave the polling/discovery queue. It does not verify accounts on a platform or obtain approval by itself. Inspect the new queue to confirm the intended scope. This also completes the path from an empty starter to the first collection.

## Optional configuration

Scheduling starts disabled. Set a local run time and authorize a supported scheduler separately only when recurring collection is requested. Verify its timezone and actual execution; a configuration file does not create a scheduler. An authorized daily run discovers new posts while polling each post only within its first 168 hours after publication. Late discoveries retain earlier gaps.

Heuristics start empty. If the user wants one, record the exact rule, its brand/platform context, limits, approval date/context and intended decision use in project configuration or notes. Label resulting recommendations `basis: user_approved_brand_heuristic`. A prior owner's thresholds and expected uplifts are not defaults, measured results or guaranteed forecasts.

Keep credentials in the environment's protected secret storage, outside briefs, registries, reports and fixture data. Setup, account approval and research access do not authorize posting, sending, paid services or account-setting changes. Verify these actions against the user's actual request.
