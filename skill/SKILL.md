---
name: trendwatch
description: Research Instagram Reels or TikTok examples, verify trends with dated observations, review video and audience responses, and turn findings into shootable tests for a brand. Use for trendwatching, competitor content research, daily metric snapshots, ideation from existing evidence, or reviewing published content tests.
metadata:
  version: "2.0"
---

# Trendwatch

Produce evidence a content team can use to decide what to shoot and what to test. Keep observations, interpretations, working heuristics and experiment results distinct. Use the requested platform and business model; do not assume an app, App Store funnel, TikTok, or AI production.

## Start with the smallest relevant mode

| Request | Work |
|---|---|
| Select accounts | Verify identity, relevance, diversity and access; deliver a shortlist with reasons |
| First research pass | Brief, access check, dated collection, baselines, detailed examples and shootable tests |
| Refresh / daily snapshots | Discover new posts in approved profiles; update eligible posts and tracked sounds; reuse media |
| Trends only | Collect current evidence on the requested platform; distinguish fresh examples, repeated patterns and measured growth |
| Ideas from existing data | Check source freshness and own experiments; create production briefs without repeating discovery |
| Production brief | Turn selected ideas into scripts, shot order, resources and measurable variants |
| Log / review experiment | Append observations, compare appropriate controls, decide whether to repeat, revise or expand |

Keep project data outside the installed skill. Find the existing project folder, `brief.md`, approved registry, prior own-account analysis, production constraints and experiment log before asking questions. Reuse established approvals. Ask only for missing goals, audience/traffic choices or operational constraints that materially change the result; continue independent work.

If this entrypoint is a symlink, resolve its real path before loading relative references or scripts.

Read [method.md](references/method.md) for a new research or trend assessment. Read only the selected platform reference: [Instagram](references/instagram.md) or [TikTok](references/tiktok.md). For detailed media review, load [video-review.md](references/video-review.md). For snapshots and project data, load [data-and-snapshots.md](references/data-and-snapshots.md). For deliverables and learning, load [production-and-release.md](references/production-and-release.md).

## Two retained working rules

The user explicitly retained these rules on 2026-09-09. Keep them available for decisions:

1. **1000 views means passing the first algorithmic gate** on a cold/new account: use this as a heuristic to flag a candidate for iteration. It does not by itself prove distribution mechanics, qualify an established account as a winner, or trigger SCALE.
2. **Trending sound increases reach by 2-3x**: retain this as an expected-benefit heuristic for prioritizing a suitable, platform-verified sound test. Do not multiply observed metrics, promise a forecast, or report that uplift as measured without a controlled result. Sound recency alone does not establish that it is trending.

Record `basis: user_retained_heuristic` when either rule motivates a decision. Other algorithmic thresholds or numerical guarantees from the old skill are not defaults. User preferences do not replace observed results.

## Research contract

Set goal/KPI, platform, audience, approved accounts, observation window, sampling rule, deliverable and depth. Account registry must include verified handle/source, inclusion reason and role (direct, adjacent, creative reference, partner, own account). Keep unavailable identities visible; do not silently substitute namesakes.

Before a large collection, test whether the current allowed access path yields publication date, numeric counters, comments, media and audio on a small varied sample. Record availability and fallback. Do not promise complete audiovisual analysis from metadata-only access.

Collect sequentially to the window boundary or a declared limit. Label partial grids. Preserve all dates that justify freshness. Select both notable candidates and comparable ordinary/weak examples; cover relevant roles instead of letting one easy account dominate.

## Non-negotiable evidence boundaries

- A fresh post is not automatically a rising trend. A single audio-use count is prevalence, not velocity. Independent authors must not be duplicated through coauthorship/reposts.
- An above-median result is an outlier, not proof that a format caused it. Compare posting author, brand and collaborator context separately where appropriate.
- Views are not unique reach or engagement rate. Reposts are not private sends. Unknown saves/retention are not zero. Cross-platform counters remain separate.
- Publication time differs from edit/comment time. Store source, timestamp precision and capture time. Never backfill an unobserved past day's metrics with today's values.
- Comments are a selected sample. Classify product intent, objections, identity/celebrity reactions, prompted replies, giveaway entries and spam separately.
- Paid partnership means disclosed collaboration, not necessarily purchased view amplification. Size, production polish or an outlier alone does not prove paid traffic or hidden ownership.
- ASR is transcription, not listening. No transcript does not prove no voice. Frame sampling does not establish absence across an entire video. State review method and unresolved fields.
- Keep confidence, signal strength and transferability separate. Do not rank with invented proxy scores for rewatching, completion or conversions.

## Daily observations: first seven days after posting

Default to one snapshot per tracked Reel per day during its first seven age-days, anchored to publication, not discovery. The daily collector discovers new posts in approved accounts and stops polling each at 168 hours. Save actual `observed_at` and `age_hours`; fixed-time daily checks are not exact 24/72/168-hour measurements. Late discoveries retain missing earlier age-days. Date-only publication metadata needs verification before an exact age-day is assigned.

Use an existing appropriate scheduler when the user authorizes recurring collection; do not schedule merely because the skill was loaded. In Codex, use the automation tool, defaulting to a thread heartbeat. Scheduling and successful source collection are separate checks. No guarantee of seven observations if access fails, the host is unavailable or discovery is late.

The implementation and day boundaries are in [data-and-snapshots.md](references/data-and-snapshots.md); use `scripts/trendwatch_data.py` to persist, deduplicate, build queues, calculate baselines and validate release evidence.

## Execution efficiency

Persist after every profile/page; resume missing fields after interruption. Reuse approved registry, unchanged media, ASR and own-account findings. Update counters as observations, not rewrites. Compute numbers once and render all prose/tables from that output. Parallelize independent local media/analysis work where authorized; do not have agents race over one controlled browser. Avoid printing raw grids, signed media URLs or unrelated browser content.

For temporary failures, make a bounded retry and then use an authorized alternative or record a gap. Repeating a blocked action indefinitely is not progress. Respect access/tool policy; no bypass, unsolicited installation, authentication change or paid service.

## Deliverable and ready state

Lead with three recommended tests and why they fit the brand. Follow with verified examples, comparison/limitations, exact coverage funnel and production briefs. Give the requested count of ideas; weaker/new hypotheses must be marked, not dressed up as observed winners.

Use [research-report.md](assets/research-report.md), [shooting-brief.md](assets/shooting-brief.md) and [experiment.md](assets/experiment.md). A fresh case needs a verified date/source; a recommendation needs references or a new-hypothesis label. Missing required evidence moves a case to a limited-evidence appendix; useful verified work can still ship with an explicit coverage status.

A production-ready test needs audience/task, product selection, hook, timed scene order, visual/voice/text/CTA plan, resources, one-variable variants, KPI and control/measurement plan. Check the actual delivery format: one local HTML is not portable when it depends on sibling media files. Provide a portable package or public source links as appropriate; publication/sending still requires authorization.

Run the data validator and meaningful behavior tests after helper changes. Validate the skill's frontmatter and reference links. For substantive methodology changes, use independent forward-testing on raw fixtures without supplying the intended answers. Review factual and creative usefulness separately.

Do not alter generic playbook rules automatically after an observation. Log brand-specific evidence and hypotheses in the project. Promote a reusable rule only after review and user authorization. Preserve history through dated corrections rather than silently revising old snapshots.
