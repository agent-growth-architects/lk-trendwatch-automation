# Data and seven-day observations

The helper is local stdlib Python 3.9+; it makes no network/browser calls. The agent collects through allowed tools, then feeds verified payloads. It does not provide Instagram access or a scheduler by itself.

## Storage and commands

Use a project-specific monitoring directory. `state.json` holds approved profile registry, canonical post metadata, append-preserved observations, audio observations and attempts. Writes are locked and atomic. Reports are generated from this state, never copied numerical prose. Do not put account/project data in the installed skill.

```
python3 scripts/trendwatch_data.py init --project PROJECT --registry REGISTRY_JSON --name BRAND_NAME
python3 scripts/trendwatch_data.py ingest --project PROJECT --input VERIFIED_BATCH_JSON
python3 scripts/trendwatch_data.py queue --project PROJECT --output QUEUE_JSON
python3 scripts/trendwatch_data.py render --project PROJECT
python3 scripts/trendwatch_data.py validate --project PROJECT
python3 scripts/trendwatch_data.py baseline --input COMPARABLE_ROWS_JSON --target REEL_ID
python3 -m unittest discover -s tests -v
```

Registry accepts a list or a previous dataset's `registry`. Preserve verification_source and coverage status. Publication owner may differ from grid handle; record resolved_author/coauthors as additional metadata and keep one canonical Reel ID across collaborators. Register only approved profiles; propose additions separately.

Batch example (values are schema examples, never upload as real observations):

```json
{
  "posts": [{"id":"REEL_ID","handle":"approved_handle","url":"https://www.instagram.com/approved_handle/reel/REEL_ID/","published_at":"2026-09-09T06:00:00Z","source":"original publication time on Reel page","audio_id":"AUDIO_ID"}],
  "observations": [{"id":"REEL_ID","observed_at":"2026-09-09T07:00:00Z","source":"Instagram visible counters; evidence file or tool capture","surface":"instagram_reel_public","metrics":{"views":1200,"likes":40,"comments":5,"reposts":1,"saves":null,"shares":null},"display":{"views":"1.2K"},"resolution":{"views":100}}],
  "audio_observations": [{"audio_id":"AUDIO_ID","observed_at":"2026-09-09T07:00:00Z","source":"Instagram audio card URL","surface":"instagram_audio_card","uses":51000,"resolution":{"uses":1000}}],
  "attempts": [{"target":"approved_handle","observed_at":"2026-09-09T07:00:00Z","status":"partial","reason":"date available; some comments inaccessible"}]
}
```

Record actual observation times, not scheduled times. Publication edits require correction_reason and retain previous timestamps. Date-only historical data may be registered as published_date but are queued for timestamp verification. Historical snapshot dates without time stay in a separate legacy source; do not invent an exact observed_at to import them.

After a publication-time correction, recalculate observation ages while retaining original ages and publication time. If two real observations move into one age-day, retain both; the earliest represents that day, while the later has `excluded_from_age_day_series: true` and a correction reason. Observations moved outside 0-168 hours also remain in history with an exclusion flag. The latest real counters and timestamp-based deltas can still use these observations; day-based comparisons must use only representatives. A later correction can restore eligibility.

## Day semantics

D1 covers age 0 up to but not including 24 hours; D2 24-48; …; D7 144-168. Exactly 168 hours ends polling. A daily fixed-clock run produces at most one successful observation per age-day and per local calendar day. It does not guarantee measurements at exact age 24/72/168 hours. Label plots with actual age. A late discovery does not reset the seven-day window. Missing days stay missing; future days are not yet observed. A separate exact-age own-experiment measurement is a different schedule and must not be implied.

At each scheduled run:
1. Preflight current permitted source access. Record failure if unavailable; do not count a successful timer as successful data.
2. Discover new posts in approved profiles through the seven-day boundary/cap. Confirm timestamps and deduplicate originals. Register metadata page by page.
3. Use queue to update only due posts. Save null for unavailable metrics; same-day duplicates are skipped. Cache actual media; no daily redownload.
4. Update linked audio-use counters once daily per ID/surface while an eligible post uses it. More uses only establish observed change; account for rounding and independent adoption evidence before calling a trend.
5. Record access gaps and coverage, validate state, generate daily report and daily-summary.json. Persist an execution log with actual start/end, discovered/attempted/successful/failed counts.
6. Stop each post at 168 hours. Continue discovery for new posts only if recurring monitoring is authorized. Do not stop the whole monitor after seven calendar days when the user meant seven days per post.

Count resolution is the rounding step, e.g. 1.2K implies step 100. A change smaller than combined rounding uncertainty is not a reliable growth claim. Negative revisions are flagged. Do not combine surfaces or substitute missing metrics with zeros. Baseline helper excludes target and declared pinned/out-of-order items and returns exact IDs/N; caller must choose comparable age/context.

## Automation boundary

Create/update the actual supported scheduler only with user authorization. In Codex prefer a thread heartbeat, preserve existing matching automation when found and avoid duplicate schedules. State schedule and source-health status separately in the final reply. Without a working scheduler, provide the prepared configuration and exact blocker; do not claim ongoing monitoring.
