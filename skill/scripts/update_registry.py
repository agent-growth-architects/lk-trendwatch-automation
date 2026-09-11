#!/usr/bin/env python3
"""Apply an explicitly approved registry without deleting post/observation history."""
import argparse
import json
from pathlib import Path
import tempfile
import trendwatch_data as tw
from setup_project import validate_registry


def update(project, registry_file):
    project=Path(project)
    config=tw.read(project/'project.json')
    rows=validate_registry(tw.read(registry_file),config['platform'])
    with tempfile.TemporaryDirectory(prefix='trendwatch-registry-') as temporary:
        temp=Path(temporary)
        tw.write(temp/'registry.json', rows)
        tw.init(temp, temp/'registry.json', timezone=config['timezone'],name=config['name'])
        profiles=tw.read(temp/'state.json')['profiles']
    def identity(row):
        return (row.get('platform',config['platform']), (row.get('handle') or row.get('name') or '').lower())
    with tw.locked(project):
        state=tw.read(project/'state.json')
        keys={identity(row) for row in profiles}
        for old in state['profiles']:
            if identity(old) not in keys:
                profiles.append({**old,'approved':False,'status':'not_in_current_registry'})
        state['profiles']=profiles
        tw.validate_state(state)
        tw.write(project/'state.json',state)
        tw.write(project/'registry.json',profiles)
    return {'profiles':len(profiles),'approved_profiles':sum(x['approved'] for x in profiles),'history_preserved':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True)
    parser.add_argument('--registry',required=True)
    args=parser.parse_args()
    print(json.dumps(update(args.project,args.registry)))
