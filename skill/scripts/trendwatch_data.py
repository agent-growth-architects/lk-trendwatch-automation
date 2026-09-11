#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local, stdlib-only trendwatch storage and calculations. No browser/network calls."""
import argparse, copy, datetime as dt, fcntl, html, json, math, os, statistics
from contextlib import contextmanager
from pathlib import Path
from zoneinfo import ZoneInfo
UTC=dt.timezone.utc

def stamp(value):
    t=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('Timestamp must include timezone')
    return t.astimezone(UTC)

def iso(t): return t.astimezone(UTC).isoformat().replace('+00:00','Z')
def now(): return iso(dt.datetime.now(UTC))
def read(path): return json.loads(Path(path).read_text())
def write(path,value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w') as f: json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

@contextmanager
def locked(project):
    p=Path(project);p.mkdir(parents=True,exist_ok=True)
    with (p/'.lock').open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        try: yield p
        finally: fcntl.flock(f,fcntl.LOCK_UN)

def age_day(post,observed_at):
    if not post.get('published_at'): return None
    hours=(stamp(observed_at)-stamp(post['published_at'])).total_seconds()/3600
    if hours<0: raise ValueError('Observation predates publication')
    return min(7,int(hours//24)+1) if hours<168 else None

def observation_status(state,post,at):
    if not post.get('published_at'): return 'needs_publication_timestamp'
    hours=(stamp(at)-stamp(post['published_at'])).total_seconds()/3600
    if hours<0: return 'future_publication'
    if hours>=168: return 'window_complete'
    day=age_day(post,at);local=stamp(at).astimezone(ZoneInfo(state['timezone'])).date().isoformat()
    prior=[o for o in state['observations'] if o['id']==post['id']]
    if any(o.get('age_day')==day for o in prior): return 'already_observed_age_day'
    if any(stamp(o['observed_at']).astimezone(ZoneInfo(state['timezone'])).date().isoformat()==local for o in prior): return 'already_observed_calendar_day'
    return 'due'

def valid_resolution(res):
    if not isinstance(res,dict): raise ValueError('resolution must be an object')
    for v in res.values():
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0: raise ValueError('Invalid positive finite resolution')

def not_future(value):
    if stamp(value)>dt.datetime.now(UTC)+dt.timedelta(minutes=5): raise ValueError('Future observation timestamp')

def numeric_metrics(m):
    if not isinstance(m,dict): raise ValueError('metrics must be an object')
    for k,v in m.items():
        if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0):
            raise ValueError('Invalid nonnegative metric '+k)

def init(project,registry=None,timezone='UTC',name='Trendwatch'):
    ZoneInfo(timezone)
    with locked(project) as p:
        if (p/'state.json').exists(): raise ValueError('Project exists; use ingest')
        rows=read(registry) if registry else []
        if isinstance(rows,dict): rows=rows['registry']
        profiles=[]
        for r in rows:
            platform=r.get('platform','instagram')
            url=r.get('profile_url')
            if not url and r.get('handle'):
                url=('https://www.tiktok.com/@' if platform=='tiktok' else 'https://www.instagram.com/')+r['handle']+'/'
            approved=r.get('approved',False)
            if not isinstance(approved,bool): raise ValueError('approved must be boolean')
            profiles.append({'name':r.get('brand',r.get('name')),'handle':r.get('handle'),'platform':platform,'approved':approved,'status':r.get('status','unverified'),'profile_url':url,'verification_source':r.get('verification_source'),'role':r.get('role','approved_brand'),'inclusion_reason':r.get('note',r.get('inclusion_reason'))})
        s={'schema_version':2,'project_name':name,'timezone':timezone,'monitor_days':7,'profiles':profiles,'posts':{},'observations':[],'audio_observations':[],'attempts':[],'created_at':now()}
        write(p/'state.json',s)
        return {'profiles':len(profiles),'project':str(p)}

def ingest(project,payload):
    with locked(project) as p:
        s=read(p/'state.json');at=now();counts={'posts':0,'observations':0,'audio_observations':0,'skipped':0,'attempts':0}
        approved={r['handle'] for r in s['profiles'] if r.get('approved') and r.get('handle')}
        for row in payload.get('posts',[]):
            row=copy.deepcopy(row)
            for k in ('id','handle','url','source'):
                if not row.get(k): raise ValueError('Post missing '+k)
            if row['handle'] not in approved: raise ValueError('Handle outside approved registry: '+row['handle'])
            if row.get('published_at'): stamp(row['published_at'])
            else:
                if not row.get('published_date'): raise ValueError('Post needs publication date or timestamp')
                dt.date.fromisoformat(row['published_date'])
            old=s['posts'].get(row['id'])
            if old and old.get('published_at') and not row.get('published_at'): row.pop('published_at',None)
            if old and old.get('published_at') and row.get('published_at') and stamp(old['published_at'])!=stamp(row['published_at']):
                if not row.get('correction_reason'): raise ValueError('Publication timestamp correction requires reason')
                row['previous_publication_times']=old.get('previous_publication_times',[])+[old['published_at']]
            row.setdefault('first_seen_at',old.get('first_seen_at',at) if old else at)
            merged={**(old or {}),**row}
            if old and old.get('published_at') and merged.get('published_at') and stamp(old['published_at'])!=stamp(merged['published_at']):
                represented_days=set()
                for observation in sorted(s['observations'],key=lambda o:stamp(o['observed_at'])):
                    if observation['id']!=row['id']: continue
                    observation.setdefault('publication_time_at_observation',old['published_at'])
                    observation.setdefault('initial_age_hours',observation['age_hours'])
                    observation.setdefault('initial_age_day',observation['age_day'])
                    hours=(stamp(observation['observed_at'])-stamp(merged['published_at'])).total_seconds()/3600
                    observation['age_hours']=round(hours,4)
                    observation['age_day']=min(7,int(hours//24)+1) if 0<=hours<168 else None
                    observation['timing_status']='reclassified_after_publication_correction' if observation['age_day'] else 'outside_window_after_publication_correction'
                    observation.pop('excluded_from_age_day_series',None)
                    observation.pop('exclusion_reason',None)
                    if observation['age_day'] is None or observation['age_day'] in represented_days:
                        observation['excluded_from_age_day_series']=True
                        observation['exclusion_reason']='outside_window_after_publication_correction' if observation['age_day'] is None else 'age_day_collision_after_publication_correction'
                    else: represented_days.add(observation['age_day'])
            s['posts'][row['id']]=merged;counts['posts']+=1
        for row in payload.get('observations',[]):
            row=copy.deepcopy(row)
            for k in ('excluded_from_age_day_series','exclusion_reason','timing_status','publication_time_at_observation','initial_age_hours','initial_age_day'):
                row.pop(k,None)
            for k in ('id','observed_at','source','surface','metrics'):
                if k not in row: raise ValueError('Observation missing '+k)
            if not row['source'] or not row['surface']: raise ValueError('Source/surface empty')
            post=s['posts'].get(row['id'])
            if not post: raise ValueError('Unknown post')
            stamp(row['observed_at']);not_future(row['observed_at']);numeric_metrics(row['metrics'])
            valid_resolution(row.get('resolution',{}))
            same=[o for o in s['observations'] if o['id']==row['id']]
            if any(o['observed_at']==row['observed_at'] for o in same): counts['skipped']+=1;continue
            status=observation_status(s,post,row['observed_at'])
            if status.startswith('already_'): counts['skipped']+=1;continue
            if status!='due': raise ValueError('Observation ineligible: '+status)
            if same and stamp(row['observed_at'])<=max(stamp(o['observed_at']) for o in same): raise ValueError('Cannot insert retrospective observation')
            row['age_hours']=round((stamp(row['observed_at'])-stamp(post['published_at'])).total_seconds()/3600,4)
            row['age_day']=age_day(post,row['observed_at']);row['ingested_at']=at
            s['observations'].append(row);counts['observations']+=1
        for row in payload.get('audio_observations',[]):
            row=copy.deepcopy(row)
            for k in ('audio_id','observed_at','source','surface','uses'):
                if k not in row: raise ValueError('Audio observation missing '+k)
            stamp(row['observed_at']);not_future(row['observed_at']);numeric_metrics({'uses':row['uses']});valid_resolution(row.get('resolution',{}))
            if not row['source'] or not row['surface'] or not row['audio_id']: raise ValueError('Audio source/surface/id empty')
            day=stamp(row['observed_at']).astimezone(ZoneInfo(s['timezone'])).date()
            prior=[o for o in s['audio_observations'] if o['audio_id']==row['audio_id'] and o['surface']==row['surface']]
            if any(stamp(o['observed_at']).astimezone(ZoneInfo(s['timezone'])).date()==day for o in prior):counts['skipped']+=1;continue
            if prior and stamp(row['observed_at'])<=max(stamp(o['observed_at']) for o in prior):raise ValueError('Retrospective audio observation')
            s['audio_observations'].append(row);counts['audio_observations']+=1
        for row in payload.get('attempts',[]):
            if not all(row.get(k) for k in ('target','observed_at','status')): raise ValueError('Attempt fields missing')
            stamp(row['observed_at']);s['attempts'].append(row);counts['attempts']+=1
        validate_state(s);write(p/'state.json',s);return counts

def queue(state,at):
    stamp(at);out=[]
    approved={r['handle'] for r in state['profiles'] if r.get('approved') and r.get('handle')}
    for post in state['posts'].values():
        if post['handle'] not in approved: continue
        status=observation_status(state,post,at)
        if status in ('due','needs_publication_timestamp'):
            out.append({**post,'status':status,'age_day':age_day(post,at) if post.get('published_at') else None})
    return {'as_of':at,'profiles_for_discovery':[r for r in state['profiles'] if r.get('approved') and r.get('handle')],'posts':out,'unresolved_profiles':[r for r in state['profiles'] if not r.get('handle')]}

def baseline(rows,target_id,metric='views',exclude_flagged=True):
    seen={};excluded=[]
    for r in rows:
        if r['id']==target_id or (exclude_flagged and r.get('pinned_or_out_of_order')): excluded.append(r['id']);continue
        value=r.get(metric)
        if value is None:continue
        numeric_metrics({metric:value})
        if r['id'] in seen and seen[r['id']]!=value:raise ValueError('Conflicting duplicate baseline ID')
        seen[r['id']]=value
    vals=list(seen.values());return {'n':len(vals),'median':statistics.median(vals) if vals else None,'ids':list(seen),'excluded_ids':excluded,'method':'leave_target_out; caller must supply comparable population'}

def changes(observations,id_key='id',metric='views'):
    groups={}
    for o in observations:groups.setdefault((o[id_key],o['surface']),[]).append(o)
    out=[]
    for (key,surface),oo in groups.items():
        oo=sorted(oo,key=lambda x:stamp(x['observed_at']))
        if len(oo)<2:continue
        prev,last=oo[-2:];get=lambda o:o.get('uses') if metric=='uses' else o['metrics'].get(metric)
        a,b=get(prev),get(last)
        if a is None or b is None:continue
        qa=prev.get('resolution',{}).get(metric,1) if isinstance(prev.get('resolution',{}),dict) else prev['resolution']
        qb=last.get('resolution',{}).get(metric,1) if isinstance(last.get('resolution',{}),dict) else last['resolution']
        delta=b-a;uncertainty=(qa+qb)/2
        out.append({id_key:key,'surface':surface,'from':prev['observed_at'],'to':last['observed_at'],'before':a,'after':b,'delta':delta,'hours':(stamp(last['observed_at'])-stamp(prev['observed_at'])).total_seconds()/3600,'rounding_uncertainty':uncertainty,'status':'counter_revision_or_decline_unresolved' if delta<0 else ('within_rounding' if abs(delta)<uncertainty else 'measured_change_not_causal_trend')})
    return out

def validate_state(s):
    if s.get('schema_version')!=2:raise ValueError('Wrong schema')
    unique=set()
    for o in sorted(s['observations'],key=lambda o:stamp(o['observed_at'])):
        post=s['posts'][o['id']]
        not_future(o['observed_at'])
        hours=(stamp(o['observed_at'])-stamp(post['published_at'])).total_seconds()/3600
        day=min(7,int(hours//24)+1) if 0<=hours<168 else None
        if day!=o['age_day']:raise ValueError('Wrong age-day')
        if not math.isclose(hours,o['age_hours'],abs_tol=0.00011):raise ValueError('Wrong age_hours')
        excluded=o.get('excluded_from_age_day_series',False)
        corrected=bool(post.get('previous_publication_times') and o.get('publication_time_at_observation'))
        if day is None and (not corrected or o.get('timing_status')!='outside_window_after_publication_correction'):raise ValueError('Ineligible observation')
        if excluded:
            if not corrected:raise ValueError('Unjustified series exclusion')
            expected='outside_window_after_publication_correction' if day is None else 'age_day_collision_after_publication_correction'
            if o.get('exclusion_reason')!=expected:raise ValueError('Wrong exclusion reason')
            if day is not None and (o['id'],day) not in unique:raise ValueError('Missing earlier day representative')
        elif day is not None:
            if (o['id'],day) in unique:raise ValueError('Duplicate age-day')
            unique.add((o['id'],day))
        if not o.get('source') or not o.get('surface'):raise ValueError('Observation evidence missing')
        numeric_metrics(o['metrics']);valid_resolution(o.get('resolution',{}))
    audio_keys=set()
    for o in s['audio_observations']:
        not_future(o['observed_at'])
        numeric_metrics({'uses':o['uses']});valid_resolution(o.get('resolution',{}))
        if not o.get('audio_id') or not o.get('source') or not o.get('surface'):raise ValueError('Audio evidence missing')
        key=(o['audio_id'],o['surface'],stamp(o['observed_at']).astimezone(ZoneInfo(s['timezone'])).date())
        if key in audio_keys:raise ValueError('Duplicate audio observation day')
        audio_keys.add(key)
    return {'status':'PASS','profiles':len(s['profiles']),'posts':len(s['posts']),'observations':len(s['observations']),'audio_observations':len(s['audio_observations'])}

def render(project):
    p=Path(project);s=read(p/'state.json')
    language=s.get('report_language', 'en')
    russian=language.lower() in ('ru', 'russian', 'русский')
    labels=(
        dict(lang='ru', suffix='ежедневные снимки', unknown='недоступно', none='нет замеров',
             note='Дни отсчитываются от публикации. Пропуски не восстановлены задним числом. Будущие дни также показаны как ещё не наблюдавшиеся; точное время каждого замера сохранено.',
             count='Проверенные наблюдения', access='Наличие расписания не подтверждает успешный доступ к источнику.',
             headers=['Публикация','Опубликована','Дни с замерами','Дни без замеров','Просмотры','Последний замер','Источник счётчиков'],
             changes='Расчёты и изменения', sources='Источники наблюдений')
        if russian else
        dict(lang='en', suffix='daily observations', unknown='unavailable', none='no observations',
             note='Age-days start at publication. Missed days are never backfilled. Future days are also listed as not yet observed; each observation retains its actual timestamp.',
             count='Verified observations', access='A configured schedule does not prove successful source access.',
             headers=['Post','Published','Observed age-days','Unobserved age-days','Views','Last observed','Counter source'],
             changes='Calculations and changes', sources='Observation sources')
    )
    report={'as_of':now(),'report_language':labels['lang'],'quality':validate_state(s),'changes':changes(s['observations']),'audio_changes':changes(s['audio_observations'],'audio_id','uses'),'posts':[]}
    for post in s['posts'].values():
        oo=sorted([o for o in s['observations'] if o['id']==post['id']],key=lambda o:stamp(o['observed_at']))
        report['posts'].append({**post,'observed_days':sorted({o['age_day'] for o in oo if o['age_day'] is not None and not o.get('excluded_from_age_day_series')}),'missing_days':[i for i in range(1,8) if not any(o['age_day']==i for o in oo)],'latest':oo[-1] if oo else None})
    write(p/'daily-summary.json',report)
    esc=lambda v:html.escape(str(v));rows=[]
    for x in report['posts']:
        latest=x['latest'];views=latest['metrics'].get('views') if latest else None
        cells=[x.get('published_at') or x.get('published_date'), x['observed_days'], x['missing_days'], views if views is not None else labels['unknown'], latest['observed_at'] if latest else labels['none'], latest['surface'] if latest else labels['none']]
        rows.append('<tr><td><a href="'+esc(x['url'])+'">'+esc(x['handle']+' / '+x['id'])+'</a></td>'+''.join('<td>'+esc(v)+'</td>' for v in cells)+'</tr>')
    title=esc(s.get('project_name','Trendwatch'))+': '+labels['suffix']
    content='<!doctype html><html lang="'+labels['lang']+'"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>body{font:16px/1.6 system-ui;max-width:1200px;margin:40px auto;padding:0 20px}table{border-collapse:collapse;font-size:14px}td,th{padding:10px;border-bottom:1px solid #ccc;text-align:left}.scroll{overflow:auto}</style><h1>'+title+'</h1><p>'+labels['note']+'</p><p>'+labels['count']+': '+str(len(s['observations']))+'. '+labels['access']+'</p><div class="scroll"><table><tr>'+''.join('<th>'+h+'</th>' for h in labels['headers'])+'</tr>'+''.join(rows)+'</table></div><p><a href="daily-summary.json">'+labels['changes']+'</a> · <a href="state.json">'+labels['sources']+'</a></p></html>'
    (p/'daily-report.html').write_text(content)
    return {'report':str(p/'daily-report.html'),**report['quality'],'changes':len(report['changes'])}

def main():
    a=argparse.ArgumentParser();sub=a.add_subparsers(dest='command',required=True)
    for cmd in ('init','ingest','queue','render','validate'):
        q=sub.add_parser(cmd);q.add_argument('--project',required=True)
        if cmd=='init':q.add_argument('--registry');q.add_argument('--timezone',default='UTC');q.add_argument('--name',default='Trendwatch')
        if cmd=='ingest':q.add_argument('--input',required=True)
        if cmd=='queue':q.add_argument('--at',default=now());q.add_argument('--output')
    q=sub.add_parser('baseline');q.add_argument('--input',required=True);q.add_argument('--target',required=True)
    x=a.parse_args()
    if x.command=='init':r=init(x.project,x.registry,x.timezone,x.name)
    elif x.command=='ingest':r=ingest(x.project,read(x.input))
    elif x.command=='queue':
        r=queue(read(Path(x.project)/'state.json'),x.at)
        if x.output:write(x.output,r);r={'queue':x.output,'posts':len(r['posts'])}
    elif x.command=='render':r=render(x.project)
    elif x.command=='validate':r=validate_state(read(Path(x.project)/'state.json'))
    else:r=baseline(read(x.input),x.target)
    print(json.dumps(r,ensure_ascii=False,allow_nan=False))
if __name__=='__main__':main()
