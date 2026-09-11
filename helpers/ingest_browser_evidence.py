#!/usr/bin/env python3
"""Normalize saved visible Instagram UI evidence. No browser or network access."""
import argparse
import datetime as dt
import importlib.util
import json
import re
from pathlib import Path

HELPER = Path(__file__).resolve().parents[1] / 'skill' / 'scripts' / 'trendwatch_data.py'
spec = importlib.util.spec_from_file_location('trendwatch_data', HELPER)
tw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tw)


def count(value):
    if not isinstance(value, str):
        return None, None
    text = value.strip().replace(',', '')
    match = re.fullmatch(r'(\d+(?:\.\d+)?)([KMB])?', text, re.I)
    if not match:
        return None, None
    factor = {'K': 1000, 'M': 1000000, 'B': 1000000000}.get((match[2] or '').upper(), 1)
    decimals = len(match[1].split('.')[1]) if '.' in match[1] else 0
    return round(float(match[1]) * factor), max(1, factor / 10 ** decimals)


def make_batch(evidence, source):
    batch = {'posts': [], 'observations': [], 'audio_observations': []}
    grids = {p['handle']: p for p in evidence['profiles']}
    seen = set()
    for i, detail in enumerate(evidence['details']):
        code = detail.get('code')
        if code in seen or (detail.get('requested_code') and code != detail['requested_code']):
            continue
        published = detail.get('published', [])
        if len(published) != 1 or not published[0].get('datetime'):
            continue
        grid = grids.get(detail['grid_handle'])
        row = next((r for r in grid['rows'] if r['code'] == code), None) if grid else None
        if not row:
            continue
        views_at = row.get('observed_at', grid['observed_at'])
        followers_at = grid.get('profile_observed_at', grid['observed_at'])
        observed_at = max([detail['observed_at'], views_at, followers_at], key=tw.stamp)
        hours = (tw.stamp(observed_at) - tw.stamp(published[0]['datetime'])).total_seconds() / 3600
        if not 0 <= hours < 168:
            continue
        seen.add(code)
        source_ref = str(source) + '#details/' + str(i)
        audio = detail.get('audio', [])
        audio_id = re.search(r'/audio/(\d+)/', audio[0]['url']).group(1) if audio else None
        post = dict(id=code, handle=grid['handle'], url=detail['url'], published_at=published[0]['datetime'],
                    source=source_ref, publication_evidence=published[0], audio_id=audio_id,
                    audio_source=audio[0] if audio else None, duration_seconds=detail.get('duration'),
                    discovery_source=grid['url'])
        if not audio:
            post.pop('audio_id')
            post.pop('audio_source')
        metrics = dict(views=None, likes=None, comments=None, reposts=None, followers=None, saves=None, shares=None)
        display, resolution, metric_times = {}, {}, {}
        followers = re.search(r'([\d,.]+[KMB]?) followers', grid['profileText'])
        for metric, text in [('views', row['display']), ('followers', followers[1] if followers else None)]:
            value, step = count(text)
            metrics[metric] = value
            if value is not None:
                display[metric], resolution[metric], metric_times[metric] = text, step, views_at if metric == 'views' else followers_at
        current = None
        for button in detail['reactionButtons']:
            icon = button.get('icon')
            if icon:
                current = {'Like': 'likes', 'Unlike': 'likes', 'Comment': 'comments', 'Repost': 'reposts'}.get(icon)
            elif current and button.get('text'):
                value, step = count(button['text'])
                if value is not None:
                    metrics[current] = value
                    display[current], resolution[current], metric_times[current] = button['text'], step, detail['observed_at']
                current = None
        batch['posts'].append(post)
        batch['observations'].append(dict(id=code, observed_at=observed_at, source=source_ref,
            surface='instagram_reel_public', metrics=metrics, display=display, resolution=resolution,
            metric_observed_at=metric_times, metric_source_surfaces={'views':'instagram_profile_reels_grid',
            'followers':'instagram_profile_header', 'reactions':'instagram_reel_detail'},
            audio_status='card_link_observed' if audio else 'card_link_not_exposed'))
    for i, audio in enumerate(evidence.get('audio', [])):
        if audio.get('requested_audio_id') != audio.get('audio_id'):
            continue
        value, step = count(audio.get('display'))
        if value is None:
            continue
        batch['audio_observations'].append(dict(audio_id=audio['audio_id'], observed_at=audio['observed_at'],
            source=str(source)+'#audio/'+str(i), source_url=audio['url'], surface='instagram_audio_card',
            uses=value, display=audio['display'], resolution={'uses':step}))
    return batch


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--project', required=True)
    args = parser.parse_args()
    source = Path(args.evidence).resolve()
    batch = make_batch(json.loads(source.read_text()), source)
    batch_path = source.with_name('verified-batch.json')
    tw.write(batch_path, batch)
    print(json.dumps({'batch':str(batch_path), **tw.ingest(args.project, batch)}, ensure_ascii=False))
