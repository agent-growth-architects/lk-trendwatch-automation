# Trendwatch

A skill for researching Instagram Reels and TikTok content around your brand's goals. Use it to choose accounts to monitor, find fresh examples, review videos and comments, prepare filming briefs, and compare the results of your own content tests.

It supports product, service, and personal brands. You define the audience, offering, language, goals, and production constraints during setup. No competitors or industry strategy are preselected.

## Start with an agent

Download this repository and give your agent the `skill/` folder with this request:

> Use the trendwatch skill in this folder for my brand. First establish what we sell, who our audience is, which platform we use, and what outcome we want. Suggest suitable accounts to study and explain your choices. Once I approve the list, check the available sources and conduct a first research pass. I need verified examples and filming briefs that fit my product. Start with a one-off project; do not create a schedule yet.

The agent will read [SKILL.md](skill/SKILL.md) and the [onboarding guide](skill/references/onboarding.md). It will reuse relevant context from your files, leave optional unknowns open, and ask about essential missing details before proceeding with work that depends on them.

If your environment supports local skills, copy the contents of `skill/` into a folder named `trendwatch` in its skills directory. Check any existing installation first to avoid overwriting your own changes. Without a skill loader, ask the agent to read `skill/SKILL.md` and its linked resources directly. Browser-tool compatibility must be checked separately.

## Define your brand

| Input | What to provide |
|---|---|
| Brand and offering | The products you sell or services you provide |
| Audience | Intended customers, language, location, and customer needs |
| Platform | Instagram or TikTok; use a separate data project for each |
| Goal and KPI | Awareness, reach, follows, product interest, or another measurable outcome |
| Production resources | Available products, people, locations, budget, and filming constraints |
| Previous results | Your own posts, experiments, and available analytics |
| Deliverable | Research, ideas, filming briefs, or daily observations |
| Timing | Your timezone; a run time is needed only for authorized recurring monitoring |

The account count depends on the research goal and collection capacity. The agent may suggest competitors, adjacent brands, creators with useful techniques, and your own account. Suggestions are not automatically approved. Each selected profile retains its role, inclusion reason, and identity-verification evidence.

## Create a data project

The Python tools run on macOS and Linux with Python 3.9 or later and an available timezone database. They use the standard library; no additional Python packages are required for data processing. On Windows, use a Linux environment such as WSL.

From the repository root, create local copies of the templates if these files do not already exist:

```bash
cp -n templates/brand.example.json brand.json
cp -n templates/registry.example.json registry.json
```

Fill in `brand.json`. The required fields are `name`, `platform`, `timezone`, and `goal`. Use an IANA timezone such as `Europe/Berlin`, `America/New_York`, or `UTC`. Add other details as they become known. `heuristics` starts empty; numerical rules from another brand are not inherited.

`registry.json` starts as an empty list. Add selected profiles using the [registry schema](skill/references/onboarding.md). Every entry needs an explicit `approved` value. If a handle is unknown, retain the brand as unresolved rather than substituting a similarly named account.

```bash
python3 skill/scripts/setup_project.py --project projects/my-brand --config brand.json --registry registry.json
python3 skill/scripts/trendwatch_data.py queue --project projects/my-brand --output projects/my-brand/queue.json
python3 skill/scripts/trendwatch_data.py validate --project projects/my-brand
```

Setup creates a separate directory containing a brief, configuration, registry, empty observation history, and an initial report. An empty report confirms project preparation; it contains no live observations yet. Setup refuses to overwrite an existing directory. For another brand, choose a different project path and supply that brand's configuration.

## Approve accounts after setup

Fill your local `registry.json` with verified profiles and mark approved entries as `approved: true`. Then apply the list:

```bash
python3 skill/scripts/update_registry.py --project projects/my-brand --registry registry.json
python3 skill/scripts/trendwatch_data.py queue --project projects/my-brand --output projects/my-brand/queue.json
```

This updates the working registry without deleting history. Profiles omitted from the new list remain stored with approval disabled and leave the queue. Use the same command to populate an initially empty registry. The command does not verify Instagram or TikTok accounts: the operator records identity evidence and the owner's approval from actual sources and decisions.

## Conduct the first research pass

The agent checks source access on a small sample: publication dates, counters, comments, video, and audio. It then collects posts from approved accounts through the selected time window or a declared limit. The report records coverage and unavailable fields.

The selection includes notable examples and ordinary posts for comparison. Detailed reviews cover the first frame, opening promise, scene order, product or service presentation, editing, subtitles, voice, music, calls to action, and comments. Each finding states what was reviewed and how.

The deliverable starts with three priority tests, or another agreed number. Each filming brief includes the audience's need, a suitable offering, first frame, timed scenes, copy, sound, resources, the variable being tested, and a measurement plan. Ideas without an observed reference are labeled as hypotheses.

## Run daily monitoring

If recurring monitoring is needed, agree on a time and timezone, then use the [automation prompt](AUTOMATION_PROMPT.md) (Russian). Setup leaves scheduling disabled and does not create a scheduler. A configuration file alone does not start any recurring work.

Monitoring keeps discovering new posts. Each post receives at most one successful observation per age-day and per project calendar day during its first 168 hours after publication. Late discovery and failed runs leave gaps. A fixed daily run time does not produce measurements at exactly 24, 72, or 168 hours of age.

Audio counts are tracked separately. A single large usage count indicates prevalence; growth requires repeated, comparable observations. Daily counter collection does not include a new full video review and script package every day.

## Access and limitations

The skill guides the agent's work; the Python tools store and validate collected data. This package does not supply an Instagram or TikTok account, API key, universal browser collector, or scheduler. The operator uses permitted tools in their own environment and checks their capabilities before promising complete coverage.

Unknown counters remain unknown. Views are not unique reach, public reposts are not private sends, and a transcript is not evidence of listening to the audio. Signal strength, evidence quality, and relevance to the brand are assessed separately.

The brief sets the language of the agent's written analysis. The built-in Python HTML report supports Russian and English labels, with English as the fallback for other languages. Scheduling, source access, collection coverage, and report generation are verified separately. Unattended operation depends on the receiving agent's environment.

## Verification and architecture

```bash
python3 -m unittest discover -s skill/tests -v
python3 -m unittest discover -s tests -v
```

- [Operator guide](AGENT_HANDOFF.md) (Russian): access, persistence, recovery, and acceptance checks.
- [Architecture](docs/architecture.md): boundaries between code, sources, and scheduling.
- [Output templates](skill/assets/research-report.md): research reports, filming briefs, and experiment logs.

Keep brand configuration, runtime data, media, and credentials out of public commits. `.gitignore` excludes standard filenames and directories, but inspect the contents before publishing your own files.
