#!/usr/bin/env python3
"""Create an isolated brand project from explicit, local configuration. No network."""
import argparse
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
import trendwatch_data as tw


def validate_registry(registry, platform):
    if not isinstance(registry, list):
        raise ValueError('Registry must be a list')
    seen = set()
    for row in registry:
        if not isinstance(row, dict) or not isinstance(row.get('approved'), bool):
            raise ValueError('Each registry entry requires explicit boolean approved')
        row.setdefault('platform', platform)
        if row['platform'] != platform:
            raise ValueError('Registry platform differs from project platform')
        handle = row.get('handle')
        if handle:
            if not isinstance(handle, str) or not re.fullmatch(r'[A-Za-z0-9_.]+', handle):
                raise ValueError('Use a handle without @ or a URL')
            if handle.lower() in seen:
                raise ValueError('Duplicate profile handle')
            seen.add(handle.lower())
        if row['approved'] and handle:
            if not row.get('verification_source') or not row.get('inclusion_reason'):
                raise ValueError('Approved known profiles need verification_source and inclusion_reason')
        if row.get('profile_url'):
            url = urlsplit(row['profile_url'])
            domains = ('instagram.com', 'www.instagram.com') if platform == 'instagram' else ('tiktok.com', 'www.tiktok.com')
            if url.scheme != 'https' or url.hostname not in domains or url.username or url.password or url.query:
                raise ValueError('Use a public profile URL on the selected platform, without credentials or query')
    return registry


def setup(project, config_file, registry_file):
    config = tw.read(config_file)
    for key in ('name', 'goal', 'timezone', 'platform'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError('Fill required brand field: ' + key)
    ZoneInfo(config['timezone'])
    if config['platform'] not in ('instagram', 'tiktok'):
        raise ValueError('Choose instagram or tiktok; use one project per platform')
    schedule = config.get('schedule', {'enabled': False, 'local_time': None})
    if not isinstance(schedule, dict) or schedule.get('enabled', False) is not False:
        raise ValueError('Setup does not enable schedules; start with enabled: false')
    if schedule.get('local_time') is not None and not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', schedule['local_time']):
        raise ValueError('local_time must be HH:MM or null')
    if not isinstance(config.get('heuristics', []), list):
        raise ValueError('heuristics must be an explicit list, empty by default')
    registry = tw.read(registry_file)
    registry = validate_registry(registry, config['platform'])
    project = Path(project).resolve()
    if project.exists():
        raise ValueError('Project path already exists; choose a new directory to preserve existing work')
    project.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.trendwatch-setup-', dir=project.parent))
    try:
        tw.write(temp / 'registry.json', registry)
        tw.init(temp, temp / 'registry.json', timezone=config['timezone'], name=config['name'])
        state = tw.read(temp / 'state.json')
        state['report_language'] = config.get('language') or 'en'
        tw.write(temp / 'state.json', state)
        config['schedule'] = schedule
        config.setdefault('heuristics', [])
        tw.write(temp / 'project.json', config)
        lines = ['# ' + config['name'], '', 'Platform: ' + config['platform'], 'Timezone: ' + config['timezone'], 'Goal: ' + config['goal']]
        for key in ('audience', 'language', 'products', 'constraints'):
            lines.append(key.title() + ': ' + str(config.get(key) or 'Not yet specified'))
        lines += ['', 'Account approval is recorded in registry.json and state.json.', 'Scheduler activation requires separate authorization.']
        (temp / 'brief.md').write_text('\n'.join(lines) + '\n')
        tw.render(temp)
        temp.rename(project)
    except BaseException:
        shutil.rmtree(temp)
        raise
    return {'project': str(project), 'name': config['name'], 'platform': config['platform'], 'timezone': config['timezone'], 'registered_profiles': len(registry), 'approved_profiles': sum(r['approved'] for r in registry), 'scheduler_created': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--registry', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(setup(args.project, args.config, args.registry), ensure_ascii=False))
    except (ValueError, KeyError) as error:
        parser.exit(2, str(error) + '\n')
