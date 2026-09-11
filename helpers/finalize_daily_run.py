#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Finalize a saved browser run with coverage, execution log and readable counters."""
import argparse
from collections import Counter
import html
import json
from pathlib import Path
from ingest_browser_evidence import tw

parser = argparse.ArgumentParser()
parser.add_argument('--project', required=True)
parser.add_argument('--run', required=True)
args = parser.parse_args()
project, run = Path(args.project).resolve(), Path(args.run).resolve()
evidence = json.loads((run / 'evidence.json').read_text())
state = tw.read(project / 'state.json')
run_id = run.name
finished = tw.now()
source_blocked = evidence.get('run_status') == 'blocked_source_access'
source_partial = evidence.get('run_status', '').startswith('partial_')
attempts = []
for row in evidence['profiles']:
    progress = evidence['profile_progress'].get(row['handle'], {})
    attempts.append(dict(target=row['url'], observed_at=row['observed_at'],
        status='completed_window' if progress.get('status') == 'seven_day_boundary_verified' else ('source_access_failed' if progress.get('status') == 'source_access_failed' else 'unavailable'),
        run_id=run_id, handle=row['handle'], grid_rows=len(row['rows']),
        dated_posts=progress.get('dated', 0), eligible_posts=progress.get('eligible', 0),
        source=str(run / 'evidence.json'), boundary=progress.get('boundary', [])))
for row in state['profiles']:
    if not row.get('handle'):
        attempts.append(dict(target=row['name'], observed_at=finished, status='not_attempted_unresolved_identity',
            run_id=run_id, source='approved registry; no replacement handle guessed'))
    elif source_blocked and row['handle'] in evidence.get('unattempted_known_handles', []):
        attempts.append(dict(target=row['handle'], observed_at=finished, status='not_attempted_source_preflight_failed',
            run_id=run_id, source=str(run / 'evidence.json')))
for failure in evidence.get('failures', []):
    attempts.append({**failure, 'run_id':run_id})
for audio in evidence.get('audio', []):
    attempts.append(dict(target=audio['url'], observed_at=audio['observed_at'], run_id=run_id,
        status='audio_count_observed' if audio.get('display') else 'audio_count_unavailable',
        source=str(run / 'evidence.json'), audio_id=audio['audio_id']))
if not any(a.get('run_id') == run_id for a in state['attempts']):
    tw.ingest(project, {'attempts': attempts})
state = tw.read(project / 'state.json')
quality = tw.validate_state(state)
for observation in state['observations']:
    for measured_at in observation.get('metric_observed_at', {}).values():
        assert tw.stamp(measured_at) <= tw.stamp(observation['observed_at'])
assert all(a['requested_audio_id'] == a['audio_id'] for a in evidence['audio'])
tw.render(project)
report = tw.read(project / 'daily-summary.json')
run_start, run_end = tw.stamp(evidence['started_at']), tw.stamp(evidence['finished_collection_at'])
run_observations = [o for o in state['observations'] if run_start <= tw.stamp(o['observed_at']) <= run_end]
run_audio = [a for a in state['audio_observations'] if run_start <= tw.stamp(a['observed_at']) <= run_end]
latest_observations = [p['latest'] for p in report['posts'] if p['latest'] is not None]
coverage = dict(approved_brands=len(state['profiles']), known_handles=sum(bool(p.get('handle')) for p in state['profiles']),
    accessible_grids=sum(bool(p['rows']) for p in evidence['profiles']),
    unresolved_brands=[p['name'] for p in state['profiles'] if not p.get('handle')],
    unavailable_handles=[p['handle'] for p in evidence['profiles'] if not p['rows']],
    numeric_grid_reels=len({r['code'] for p in evidence['profiles'] for r in p['rows'] if r['display']}),
    discovered_grid_reels=len({r['code'] for p in evidence['profiles'] for r in p['rows']}),
    dated_detail_pages=len([d for d in evidence['details'] if d.get('published')]),
    profiles_with_verified_window=sum(p['status'] == 'seven_day_boundary_verified' for p in evidence['profile_progress'].values()),
    tracked_posts=len(state['posts']), tracked_profiles=len({p['handle'] for p in state['posts'].values()}),
    new_daily_snapshots=len(run_observations), retained_prior_snapshots=len(state['observations'])-len(run_observations),
    new_audio_snapshots=len(run_audio), total_audio_snapshots=len(state['audio_observations']),
    total_observations=len(state['observations']),
    attempted_profiles=len(evidence['profiles']),
    unattempted_known_handles=evidence.get('unattempted_known_handles', []),
    pending_detail_candidates=len(evidence.get('pending_detail_candidates', [])),
    due_posts_at_run_start=len(evidence.get('due_post_ids_at_start', [])),
    last_successful_reel_observation=max((o['observed_at'] for o in state['observations']), key=tw.stamp, default=None),
    last_successful_audio_observation=max((o['observed_at'] for o in state['audio_observations']), key=tw.stamp, default=None),
    audio_link_unexposed=sum(not p.get('audio_id') for p in state['posts'].values()),
    metric_availability_this_run={k:sum(o['metrics'].get(k) is not None for o in run_observations)
                         for k in ['views','likes','comments','reposts','followers','saves','shares']},
    metric_availability={k:sum(o['metrics'].get(k) is not None for o in latest_observations)
                         for k in ['views','likes','comments','reposts','followers','saves','shares']})
execution = dict(run_id=run_id, started_at=evidence['started_at'], finished_collection_at=evidence['finished_collection_at'],
    finished_at=finished, status=evidence.get('run_status', 'completed_with_known_coverage_gaps'), coverage=coverage, quality=quality,
    source_health=evidence.get('source_health', 'available_with_recorded_gaps'),
    failure_summary=evidence.get('failure_summary'),
    attempt_statuses=dict(Counter(a['status'] for a in attempts)),
    measurement_note='Individual metric timestamps retained; comparable intervals: '+str(len(report['changes'])),
    media_note='Daily counter collection only; media not downloaded or re-reviewed.',
    verification='State validator, metric timestamps, source/audio IDs and local links checked; no browser visual QA of local file.')
report.update(run_id=run_id, coverage=coverage, execution=execution)
tw.write(run / 'execution.json', execution)
tw.write(project / 'daily-summary.json', report)

def esc(value):
    return html.escape(str(value))

def number(value):
    return 'н/д' if value is None else f'{value:,.0f}'.replace(',', ' ')

rows = []
for post in report['posts']:
    latest = post['latest']
    if latest is None:
        continue
    metrics = latest['metrics']
    rows.append('<tr><td><a href="'+esc(post['url'])+'">'+esc(post['handle'])+'<br>'+esc(post['id'])+'</a></td>'
        +'<td>'+esc(post['published_at'])+'</td><td>'+esc(latest['age_day'])+'</td>'
        +''.join('<td>'+number(metrics.get(k))+'</td>' for k in ['views','likes','comments','reposts'])
        +'<td>'+esc(latest['observed_at'])+'</td></tr>')
audio_latest = {}
for audio in state['audio_observations']:
    audio_latest[audio['audio_id']] = audio
audio_rows = []
for audio_id, audio in audio_latest.items():
    linked = [p for p in state['posts'].values() if p.get('audio_id') == audio_id]
    name = next((p.get('audio_source', {}).get('title') for p in linked if p.get('audio_source')), audio_id)
    url = next((p.get('audio_source', {}).get('url') for p in linked if p.get('audio_source')), audio.get('source_url'))
    if not url:
        url = 'https://www.instagram.com/reels/audio/'+audio_id+'/'
    audio_rows.append('<tr><td><a href="'+esc(url)+'">'+esc(name)+'</a></td><td>'+number(audio['uses'])
        +'</td><td>'+esc(audio['observed_at'])+'</td></tr>')
profile_rows = []
for profile in state['profiles']:
    handle = profile.get('handle')
    progress = evidence['profile_progress'].get(handle, {})
    status = 'Граница 7 дней проверена' if progress.get('status') == 'seven_day_boundary_verified' else ('Профиль не установлен' if not handle else ('Ошибка доступа к источнику' if progress.get('status') == 'source_access_failed' else ('Не проверен: сбой контрольного запроса' if handle in evidence.get('unattempted_known_handles', []) else 'Страница недоступна')))
    profile_rows.append('<tr><td>'+esc(profile['name'])+'</td><td>'+esc(handle or 'н/д')+'</td><td>'+status
        +'</td><td>'+str(progress.get('dated', 0))+'</td><td>'+str(progress.get('eligible', 0))+'</td></tr>')
markup = '''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LK Urban Dress: ежедневные снимки</title><style>body{font:16px/1.55 system-ui;max-width:1400px;margin:32px auto;padding:0 20px;color:#202020}table{border-collapse:collapse;font-size:13px;width:100%}th,td{padding:10px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}th{background:#f4f4f4}.scroll{overflow:auto}summary{cursor:pointer;font-weight:650;margin:20px 0}.note{background:#f5f5f5;padding:16px;border-radius:10px}a{color:#245c8c}</style>
<h1>LK Urban Dress: ежедневные снимки</h1>'''
markup += '<p>Проход '+esc(run_id)+'. Завершён: '+esc(finished)+'. Все временные метки в таблицах указаны в UTC; расписание работает по Москве.</p>'
if source_blocked:
    markup += '<div class="note"><b>Сбор не выполнен: источник недоступен.</b> '+esc(evidence.get('failure_summary', ''))+' Ожидали замера известных роликов: '+str(coverage['due_posts_at_run_start'])+'. Новые публикации не проверены. Ниже показаны прежние наблюдения; последний сохранённый замер Reels: '+esc(coverage['last_successful_reel_observation'])+'.</div>'
elif source_partial:
    markup += '<div class="note"><b>Доступ к Instagram восстановился; повторный сбор выполнен частично.</b> '+esc(evidence.get('failure_summary', ''))+' Непроверенных карточек в очереди этого прохода: '+str(coverage['pending_detail_candidates'])+'. В таблицах сохранены фактические даты замеров: старые показатели не считаются сегодняшними.</div>'
markup += '<p><b>Новые снимки: Reels '+str(coverage['new_daily_snapshots'])+', аудио '+str(coverage['new_audio_snapshots'])+'.</b> Всего Reels в базе: '+str(coverage['tracked_posts'])+', профилей: '+str(coverage['tracked_profiles'])+', снимков аудио: '+str(coverage['total_audio_snapshots'])+'.</p>'
markup += '<p>Одобрено брендов: '+str(coverage['approved_brands'])+'; доступны сетки: '+str(coverage['accessible_grids'])+'. Карточек с проверенными датами публикаций: '+str(coverage['dated_detail_pages'])+'; уникальных Reels в сетках: '+str(coverage['discovered_grid_reels'])+'. Полный видеоразбор в этом ежедневном проходе не проводился.</p>'
series_note = 'Это первый дневной срез. Сопоставимых ежедневных серий пока нет, поэтому выводов о росте трендов нет.' if not report['changes'] else 'Интервалы между сопоставимыми замерами: '+str(len(report['changes']))+'. Изменения и точность счётчиков сохранены в JSON; их причинная интерпретация требует отдельного анализа.'
if source_blocked:
    series_note = 'Сегодняшний период остаётся пропуском. Сравнение с сегодняшними показателями невозможно. Сохранённая история не заменяет свежий замер.'
markup += '<div class="note">'+series_note+' Дни D1–D7 отсчитываются от публикации. Поздно найденные ролики имеют пропуски. н/д означает, что счётчик не был доступен; это не ноль. Просмотры не равны уникальному охвату, репосты не равны личным отправкам.</div>'
markup += '<p>В последних сохранённых наблюдениях просмотры доступны у '+str(coverage['metric_availability']['views'])+' из '+str(coverage['tracked_posts'])+' роликов, лайки у '+str(coverage['metric_availability']['likes'])+', комментарии у '+str(coverage['metric_availability']['comments'])+', репосты у '+str(coverage['metric_availability']['reposts'])+'. Сохранения и личные отправки публично не получены. Ссылка на аудиокарточку не отобразилась у '+str(coverage['audio_link_unexposed'])+' роликов.</p>'
markup += '<h2>Сохранённые показатели Reels</h2><p>Счётчики сетки и карточки могут быть сняты в разное время. Точные времена по каждому показателю сохранены в JSON.</p><div class="scroll"><table><tr><th>Ролик</th><th>Опубликован</th><th>День</th><th>Просмотры</th><th>Лайки</th><th>Комментарии</th><th>Репосты</th><th>Снимок собран</th></tr>'+''.join(rows)+'</table></div>'
markup += '<details><summary>Аудиокарточки: '+str(len(audio_rows))+'</summary><div class="scroll"><table><tr><th>Аудио</th><th>Использований</th><th>Замер</th></tr>'+''.join(audio_rows)+'</table></div></details>'
markup += '<details><summary>Покрытие брендов: '+str(coverage['approved_brands'])+'</summary><div class="scroll"><table><tr><th>Бренд</th><th>Профиль</th><th>Статус</th><th>Карточек с датами</th><th>В окне 7 дней</th></tr>'+''.join(profile_rows)+'</table></div></details>'
markup += '<p><a href="daily-summary.json">Расчёты и покрытие</a> · <a href="state.json">История наблюдений</a> · <a href="runs/'+esc(run_id)+'/evidence.json">Исходные данные прохода</a> · <a href="runs/'+esc(run_id)+'/execution.json">Журнал выполнения</a></p></html>'
(project / 'daily-report.html').write_text(markup)
print(json.dumps(execution, ensure_ascii=False))
