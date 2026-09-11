"""Isolated integration checks for new users, brands and timezones."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def cli(self, script, *args, ok=True):
        result = subprocess.run([sys.executable, str(ROOT / script), *map(str, args)], capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def create(self, name='Cycle <Corner>', zone='Europe/Berlin', registry=None, extra=None, target='project', ok=True):
        config = dict(name=name, platform='instagram', timezone=zone, goal='Appointment enquiries', audience='Local commuters', language='en', schedule={'enabled': False, 'local_time': None}, heuristics=[])
        config.update(extra or {})
        cfg = self.root / (target + '-brand.json')
        reg = self.root / (target + '-registry.json')
        cfg.write_text(json.dumps(config));reg.write_text(json.dumps(registry or []))
        self.cli('skill/scripts/setup_project.py', '--project', self.root / target, '--config', cfg, '--registry', reg, ok=ok)
        return self.root / target

    def test_two_brands_are_isolated_and_reports_use_their_names(self):
        a = self.create(target='a')
        b = self.create(name='Cloud School', zone='America/New_York', target='b')
        sa = json.loads((a / 'state.json').read_text());sb = json.loads((b / 'state.json').read_text())
        self.assertEqual((sa['project_name'], sa['timezone']), ('Cycle <Corner>', 'Europe/Berlin'))
        self.assertEqual((sb['project_name'], sb['timezone']), ('Cloud School', 'America/New_York'))
        self.assertEqual(sa['profiles'], []);self.assertEqual(sb['posts'], {})
        self.assertIn('Cycle &lt;Corner&gt;', (a / 'daily-report.html').read_text())
        self.assertIn('lang="en"', (a / 'daily-report.html').read_text())
        self.assertIn('daily observations', (a / 'daily-report.html').read_text())
        self.assertNotIn('Cycle', (b / 'daily-report.html').read_text())
        self.assertFalse(json.loads((b / 'project.json').read_text())['schedule']['enabled'])

    def test_invalid_or_missing_inputs_leave_no_partial_project(self):
        for i, extra in enumerate([{'name': ''}, {'timezone': ''}, {'platform': 'both'}, {'schedule': {'enabled': True}}, {'goal': ''}]):
            project = self.create(extra=extra, target='bad' + str(i), ok=False)
            self.assertFalse(project.exists())

    def test_existing_project_is_preserved(self):
        project = self.create()
        before = (project / 'state.json').read_bytes()
        self.create(name='Replacement', ok=False)
        self.assertEqual(before, (project / 'state.json').read_bytes())

    def test_unapproved_accounts_are_not_queued(self):
        project = self.create(registry=[dict(name='Candidate', handle='candidate', platform='instagram', approved=False)])
        queue = json.loads(self.cli('skill/scripts/trendwatch_data.py', 'queue', '--project', project).stdout)
        self.assertEqual(queue['profiles_for_discovery'], [])
        self.assertEqual(len(json.loads((project / 'state.json').read_text())['profiles']), 1)

    def test_mixed_platform_and_implicit_approval_are_rejected(self):
        for i, row in enumerate([dict(handle='candidate'), dict(handle='candidate', approved=True), dict(handle='candidate', approved=False, platform='tiktok')]):
            project = self.create(registry=[row], target='invalid'+str(i), ok=False)
            self.assertFalse(project.exists())

    def test_timezone_changes_calendar_day_deduplication(self):
        row = dict(name='Reference', handle='reference', approved=True, verification_source='Synthetic test', inclusion_reason='Synthetic test')
        for i, (zone, expected) in enumerate([('UTC', 1), ('America/Los_Angeles', 2)]):
            project = self.create(zone=zone, registry=[row], target='zone'+str(i))
            batch = {'posts': [dict(id='p', handle='reference', url='https://example.com/p', source='synthetic fixture', published_at='2020-01-01T08:00:00Z')], 'observations': [dict(id='p', observed_at=t, source='synthetic fixture', surface='instagram_reel_public', metrics={'views': n, 'saves': None}) for t,n in [('2020-01-02T07:00:00Z', 10), ('2020-01-02T09:00:00Z', 20)]]}
            f=self.root/'batch.json';f.write_text(json.dumps(batch))
            self.cli('skill/scripts/trendwatch_data.py', 'ingest', '--project', project, '--input', f)
            state=json.loads((project/'state.json').read_text());self.assertEqual(len(state['observations']), expected)

    def test_approve_after_empty_setup_then_revoke_preserves_history(self):
        project=self.create()
        registry=self.root/'approved.json'
        registry.write_text(json.dumps([dict(name='Reference',handle='reference',approved=True,verification_source='Synthetic fixture',inclusion_reason='Synthetic fixture')]))
        self.cli('skill/scripts/update_registry.py','--project',project,'--registry',registry)
        queued=json.loads(self.cli('skill/scripts/trendwatch_data.py','queue','--project',project).stdout)
        self.assertEqual(len(queued['profiles_for_discovery']),1)
        batch=self.root/'batch.json'
        batch.write_text(json.dumps({'posts':[dict(id='p',handle='reference',url='https://example.com/p',source='synthetic fixture',published_at='2020-01-01T00:00:00Z')],'observations':[dict(id='p',observed_at='2020-01-01T01:00:00Z',source='synthetic fixture',surface='instagram_reel_public',metrics={'views':10})]}))
        self.cli('skill/scripts/trendwatch_data.py','ingest','--project',project,'--input',batch)
        before=json.loads((project/'state.json').read_text())
        registry.write_text('[]')
        self.cli('skill/scripts/update_registry.py','--project',project,'--registry',registry)
        after=json.loads((project/'state.json').read_text())
        self.assertEqual(before['posts'],after['posts']);self.assertEqual(before['observations'],after['observations'])
        queue=json.loads(self.cli('skill/scripts/trendwatch_data.py','queue','--project',project,'--at','2020-01-02T01:00:00Z').stdout)
        self.assertEqual(queue['posts'],[]);self.assertEqual(queue['profiles_for_discovery'],[])

    def test_instagram_finalizer_uses_brand_timezone_and_honest_status(self):
        project = self.create(name='Workshop & Co', zone='Asia/Tokyo', registry=[dict(name='Candidate', handle='candidate', approved=False)])
        run = project / 'runs' / 'synthetic';run.mkdir(parents=True)
        evidence=dict(started_at='2020-01-01T00:00:00Z', finished_collection_at='2020-01-01T01:00:00Z', run_status='partial_source_timeout', profiles=[], details=[], audio=[], profile_progress={}, failure_summary='Synthetic timeout')
        (run/'evidence.json').write_text(json.dumps(evidence))
        self.cli('helpers/finalize_daily_run.py', '--project', project, '--run', run)
        markup=(project/'daily-report.html').read_text()
        self.assertIn('Workshop &amp; Co', markup);self.assertIn('Asia/Tokyo', markup)
        self.assertNotIn('восстановился', markup)
        self.assertEqual(json.loads((project/'daily-summary.json').read_text())['coverage']['approved_brands'],0)
        evidence['run_status']='in_progress';(run/'evidence.json').write_text(json.dumps(evidence))
        before=(project/'daily-report.html').read_bytes()
        self.cli('helpers/finalize_daily_run.py', '--project', project, '--run', run, ok=False)
        self.assertEqual(before,(project/'daily-report.html').read_bytes())


if __name__ == '__main__':
    unittest.main()
