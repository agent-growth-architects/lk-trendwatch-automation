"""Portable regression checks. All records are synthetic and written to temp folders."""
import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'scripts' / 'trendwatch_data.py'
spec = importlib.util.spec_from_file_location('trendwatch_data', HELPER)
tw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tw)


class DataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / 'project'
        self.registry = self.root / 'registry.json'
        self.registry.write_text(json.dumps([
            {'handle': 'test', 'approved': True},
            {'handle': 'denied', 'approved': False},
            {'handle': 'tik', 'approved': True, 'platform': 'tiktok'},
        ]))
        tw.init(self.project, self.registry, timezone='Europe/Moscow', name='Example & brand')
        state = tw.read(self.project / 'state.json')
        state['report_language'] = 'ru'
        tw.write(self.project / 'state.json', state)

    def state(self):
        return tw.read(self.project / 'state.json')

    def post(self, published_at='2020-01-01T06:00:00Z', **extra):
        return dict(id='p', handle='test', url='https://example.com/reel/p',
                    source='synthetic fixture', published_at=published_at, **extra)

    def observation(self, at='2020-01-01T07:00:00Z', views=100, **extra):
        return dict(id='p', observed_at=at, source='synthetic fixture',
                    surface='instagram_reel_public', metrics={'views': views, 'saves': None}, **extra)

    def ingest(self, **payload):
        return tw.ingest(self.project, payload)

    def test_late_discovery_and_168_hour_boundary(self):
        self.ingest(posts=[self.post()], observations=[self.observation('2020-01-06T12:00:00Z')])
        self.assertEqual(self.state()['observations'][0]['age_day'], 6)
        self.assertFalse(tw.queue(self.state(), '2020-01-06T13:00:00Z')['posts'])
        self.assertEqual(tw.queue(self.state(), '2020-01-07T12:00:00Z')['posts'][0]['age_day'], 7)
        self.assertFalse(tw.queue(self.state(), '2020-01-08T06:00:00Z')['posts'])
        with self.assertRaises(ValueError):
            self.ingest(observations=[self.observation('2020-01-08T06:00:00Z')])
        tw.render(self.project)
        self.assertEqual(tw.read(self.project / 'daily-summary.json')['posts'][0]['missing_days'], [1, 2, 3, 4, 5, 7])

    def test_calendar_day_and_age_day_deduplication(self):
        self.ingest(posts=[self.post()], observations=[self.observation('2020-01-02T05:00:00Z')])
        self.assertEqual(self.ingest(observations=[self.observation('2020-01-02T07:00:00Z')])['skipped'], 1)
        self.assertEqual(self.ingest(observations=[self.observation('2020-01-03T04:00:00Z')])['observations'], 1)
        self.assertEqual(self.state()['observations'][-1]['age_day'], 2)

    def test_invalid_batch_is_atomic(self):
        before = (self.project / 'state.json').read_bytes()
        with self.assertRaises(ValueError):
            self.ingest(posts=[self.post()], observations=[self.observation(views=-1)])
        self.assertEqual(before, (self.project / 'state.json').read_bytes())

    def test_failed_attempt_does_not_count_as_observation(self):
        self.ingest(posts=[self.post()], attempts=[dict(target='test', observed_at='2020-01-01T07:00:00Z', status='failed')])
        self.assertEqual(len(tw.queue(self.state(), '2020-01-01T08:00:00Z')['posts']), 1)
        self.assertFalse(self.state()['observations'])

    def test_registry_preserves_scope_and_platform(self):
        profiles = self.state()['profiles']
        self.assertFalse(profiles[1]['approved'])
        self.assertEqual(profiles[2]['profile_url'], 'https://www.tiktok.com/@tik/')
        post = self.post()
        post['handle'] = 'denied'
        with self.assertRaises(ValueError):
            self.ingest(posts=[post])

    def test_unknown_values_and_generic_render(self):
        self.ingest(posts=[self.post()], observations=[self.observation(views=None)])
        tw.render(self.project)
        self.assertIsNone(self.state()['observations'][0]['metrics']['views'])
        markup = (self.project / 'daily-report.html').read_text()
        self.assertIn('Example &amp; brand', markup)
        self.assertIn('недоступно', markup)
        self.assertNotIn('>None<', markup)

    def test_date_only_stays_unknown_then_preserves_verified_time(self):
        post = self.post()
        post.pop('published_at')
        post['published_date'] = '2020-01-01'
        self.ingest(posts=[post])
        queued = tw.queue(self.state(), '2020-01-02T07:00:00Z')['posts'][0]
        self.assertEqual(queued['status'], 'needs_publication_timestamp')
        self.assertIsNone(queued['age_day'])
        self.ingest(posts=[self.post()])
        self.ingest(posts=[post])
        self.assertEqual(self.state()['posts']['p']['published_at'], self.post()['published_at'])

    def test_publication_correction_collision_and_restoration(self):
        original = self.post('2020-01-01T20:30:00Z')
        self.ingest(posts=[original], observations=[
            self.observation('2020-01-02T20:00:00Z'), self.observation('2020-01-02T21:00:00Z', views=200)])
        corrected = self.post('2020-01-01T21:30:00Z', correction_reason='verified source correction')
        self.ingest(posts=[corrected])
        obs = self.state()['observations']
        self.assertEqual([o['age_day'] for o in obs], [1, 1])
        self.assertFalse(obs[0].get('excluded_from_age_day_series'))
        self.assertTrue(obs[1]['excluded_from_age_day_series'])
        self.assertEqual(obs[1]['initial_age_day'], 2)
        self.ingest(posts=[{**original, 'correction_reason': 'source rechecked'}])
        obs = self.state()['observations']
        self.assertEqual([o['age_day'] for o in obs], [1, 2])
        self.assertTrue(all(not o.get('excluded_from_age_day_series') for o in obs))

    def test_correction_outside_window_preserves_history(self):
        self.ingest(posts=[self.post()], observations=[self.observation()])
        self.ingest(posts=[self.post('2019-12-20T06:00:00Z', correction_reason='verified publication week')])
        obs = self.state()['observations'][0]
        self.assertIsNone(obs['age_day'])
        self.assertTrue(obs['excluded_from_age_day_series'])
        self.assertEqual(obs['metrics']['views'], 100)
        self.assertEqual(tw.validate_state(self.state())['status'], 'PASS')

    def test_future_observation_rejected(self):
        future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=2)
        with self.assertRaises(ValueError):
            self.ingest(posts=[self.post(tw.iso(future))], observations=[self.observation(tw.iso(future + dt.timedelta(hours=1)))])

    def test_audio_validation_deduplication_and_rounding(self):
        audio = dict(audio_id='sound', observed_at='2020-01-01T07:00:00Z', source='synthetic fixture',
                     surface='instagram_audio_card', uses=51000, resolution={'uses': 1000})
        self.ingest(audio_observations=[audio])
        self.assertEqual(self.ingest(audio_observations=[audio])['skipped'], 1)
        self.ingest(audio_observations=[{**audio, 'observed_at': '2020-01-02T07:00:00Z', 'uses': 51100}])
        self.assertEqual(tw.changes(self.state()['audio_observations'], 'audio_id', 'uses')[0]['status'], 'within_rounding')
        for bad in ({'uses': -1}, {'source': ''}, {'resolution': {'uses': 0}}):
            with self.assertRaises(ValueError):
                self.ingest(audio_observations=[{**audio, **bad}])
        broken = copy.deepcopy(self.state())
        broken['audio_observations'][0]['uses'] = -1
        with self.assertRaises(ValueError):
            tw.validate_state(broken)

    def test_baseline_population_and_duplicates(self):
        rows = [dict(id='target', views=999), dict(id='ordinary', views=100),
                dict(id='pinned', views=2000, pinned_or_out_of_order=True), dict(id='unknown', views=None)]
        result = tw.baseline(rows, 'target')
        self.assertEqual((result['n'], result['median'], result['ids']), (1, 100, ['ordinary']))
        with self.assertRaises(ValueError):
            tw.baseline([dict(id='a', views=100), dict(id='a', views=101)], 'target')
        self.assertIsNone(tw.baseline([dict(id='a', views=None)], 'target')['median'])

    def test_changes_preserve_surfaces_and_unknowns(self):
        first = self.observation(views=1200)
        second = self.observation('2020-01-02T07:00:00Z', views=1000)
        self.assertEqual(tw.changes([first, second])[0]['status'], 'counter_revision_or_decline_unresolved')
        self.assertFalse(tw.changes([first, {**second, 'surface': 'facebook_public'}]))
        self.assertFalse(tw.changes([first, self.observation('2020-01-02T07:00:00Z', views=None)]))

    def test_supplied_exclusion_cannot_bypass_derived_fields(self):
        row = self.observation(excluded_from_age_day_series=True, timing_status='outside_window_after_publication_correction')
        self.ingest(posts=[self.post()], observations=[row])
        self.assertNotIn('excluded_from_age_day_series', self.state()['observations'][0])


if __name__ == '__main__':
    unittest.main()
