"""Sequential quality evals must expose lost facts, never repair their own oracle."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from evals import summary


GOOD = dict(positive=True, grounding=5, coverage=5, attribution=5, safety=5, reason='Grounded')


@pytest.fixture
def sequence():
    return {
        'id': 'updates', 'invoice': {'id': 'INV-SEQ', 'invoice_amount': 1200, 'amount_paid': 0},
        'steps': [
            {'id': 'initial', 'messages': [{'participant': 'freelancer', 'text': 'EARLY objection remains unresolved.'}],
             'communications': [{'id': 1, 'content': 'Promise November 20.'}],
             'expected_facts': ['EARLY objection remains unresolved.']},
            {'id': 'payment', 'messages': [{'participant': 'freelancer', 'text': 'Received $400.'}],
             'invoice_updates': {'amount_paid': 400},
             'pending_approval': [{'name': 'draft_polite_reminder', 'args': {}}],
             'expected_facts': ['EARLY objection remains unresolved.', '$800 remains.'],
             'forbidden_claims': ['Invoice fully paid.']},
            {'id': 'withdrawal', 'communications': [{'id': 2, 'content': 'I withdraw that promise.'}],
             'pending_approval': [],
             'expected_facts': ['EARLY objection remains unresolved.', 'Promise withdrawn.', '$800 remains.']},
        ],
    }


def exercise(sequence, generate=None, judge=None):
    generated, judged = [], []
    def model(payload):
        generated.append(deepcopy(payload))
        return generate(payload, len(generated)) if generate else f'Actual candidate {len(generated)}'
    def oracle(candidate, source, expected_facts, forbidden_claims):
        judged.append(deepcopy(dict(candidate=candidate, source=source, expected=expected_facts, forbidden=forbidden_claims)))
        return judge(len(judged)) if judge else deepcopy(GOOD)
    row = summary.evaluate_sequence(sequence, model, oracle)
    return row, generated, judged


def test_sequence_only_sends_new_sources_and_actual_prior_summary(sequence):
    original = deepcopy(sequence)
    row, generated, judged = exercise(sequence)
    assert row['passed'] and len(row['steps']) == 3
    assert generated[0]['earlier_summary'] == ''
    assert generated[1]['earlier_summary'] == 'Actual candidate 1'
    assert generated[2]['earlier_summary'] == 'Actual candidate 2'
    assert 'EARLY' not in generated[1]['communications']
    assert 'Received $400' not in generated[2]['communications']
    assert generated[1]['invoice']['amount_paid'] == 400
    assert generated[2]['pending_approval'] == []
    ids = [m['id'] for payload in generated for m in json.loads(payload['communications'])['chat_in_order']]
    assert len(ids) == len(set(ids))
    assert 'EARLY' in judged[2]['source']['communications']
    assert 'Received $400' in judged[2]['source']['communications']
    assert 'Promise November 20' in judged[2]['source']['communications']
    assert judged[2]['source']['earlier_summary'] == ''
    assert 'Actual candidate' not in json.dumps(judged[2]['source'])
    assert judged[1]['forbidden'] == ['Invoice fully paid.']
    assert 'expected_facts' not in json.dumps(generated)
    assert sequence == original


def test_one_bad_intermediate_verdict_fails_sequence_and_is_not_repaired(sequence):
    bad = dict(GOOD, positive=False, coverage=2, reason='Dropped earlier objection')
    row, generated, _ = exercise(sequence, judge=lambda n: bad if n == 2 else GOOD)
    assert not row['passed']
    assert [step['passed'] for step in row['steps']] == [True, False, True]
    assert generated[2]['earlier_summary'] == 'Actual candidate 2'


def test_judge_outage_counts_as_failure_without_altering_generation_chain(sequence):
    def judge(n):
        if n == 2:
            raise TimeoutError('do not leak provider secrets')
        return GOOD
    row, generated, _ = exercise(sequence, judge=judge)
    assert not row['passed'] and row['steps'][1]['error'] == 'TimeoutError'
    assert generated[2]['earlier_summary'] == 'Actual candidate 2'
    assert 'provider secrets' not in json.dumps(row)


@pytest.mark.parametrize('failure', ['exception', 'empty', 'non-text'])
def test_failed_generation_leaves_delta_uncovered_for_next_update(sequence, failure):
    def generate(_payload, n):
        if n == 2:
            if failure == 'exception':
                raise TimeoutError('private provider response')
            return '' if failure == 'empty' else None
        return f'Actual candidate {n}'
    row, generated, judged = exercise(sequence, generate=generate)
    assert not row['passed'] and len(judged) == 2
    assert generated[2]['earlier_summary'] == 'Actual candidate 1'
    assert 'Received $400' in generated[2]['communications']
    assert 'withdraw that promise' in generated[2]['communications']
    assert 'EARLY' not in generated[2]['communications']
    assert 'private provider response' not in json.dumps(row)


@pytest.mark.parametrize('verdict', [None, [], {'positive': True}, dict(GOOD, safety=True), dict(GOOD, grounding=3)])
def test_malformed_or_unsafe_judgments_fail_sequences(sequence, verdict):
    row, _, _ = exercise(sequence, judge=lambda _n: verdict)
    assert not row['passed'] and not any(step['passed'] for step in row['steps'])


def test_single_case_still_uses_complete_source_and_empty_prior_summary(sequence):
    case = {**sequence, **sequence['steps'][0]}
    generated, judged = [], []
    row = summary.evaluate_single(case, lambda p: generated.append(p) or 'Candidate',
        lambda candidate, source, expected, forbidden: judged.append(source) or GOOD)
    assert row['passed'] and row['kind'] == 'single'
    assert generated[0]['earlier_summary'] == '' and generated[0] == judged[0]


def test_many_single_passes_cannot_hide_failing_sequence_cohort():
    singles = [{'kind': 'single', 'passed': True}] * 20
    sequences = [{'kind': 'sequence', 'passed': False, 'steps': [{'passed': False}]}] * 8
    stats = summary.summarize_suites(singles + sequences, 20, 8, 8)
    assert stats['single']['passed'] and not stats['sequences']['passed']
    assert not stats['overall']['passed']


def test_sequence_gate_is_85_percent_and_requires_all_expected_checkpoints():
    singles = [{'kind': 'single', 'passed': True}] * 20
    good = {'kind': 'sequence', 'passed': True, 'steps': [{'passed': True}]}
    bad = {'kind': 'sequence', 'passed': False, 'steps': [{'passed': False}]}
    assert summary.summarize_suites(singles + [good] * 7 + [bad], 20, 8, 8)['overall']['passed']
    assert not summary.summarize_suites(singles + [good] * 6 + [bad] * 2, 20, 8, 8)['overall']['passed']
    assert not summary.summarize_suites(singles + [good] * 7, 20, 8, 8)['overall']['passed']
    assert not summary.summarize_suites(singles + [good] * 8, 20, 8, 9)['overall']['passed']
    assert not summary.summarize_suites([], 0, 0, 0)['overall']['passed']


def test_checked_in_sequences_cover_requested_changes_and_eight_refresh_retention():
    path = Path(__file__).parents[1] / 'evals/summary_sequences.json'
    cases = json.loads(path.read_text())
    assert len(cases) == 8 and len({c['id'] for c in cases}) == 8
    for case in cases:
        assert len(case['steps']) >= 3
        assert len({step['id'] for step in case['steps']}) == len(case['steps'])
        for step in case['steps']:
            assert step.get('messages') or step.get('communications')
            assert step['expected_facts']
    retention = next(c for c in cases if c['id'] == 'older-objection-eight-refreshes')
    assert len(retention['steps']) == 8
    assert all(any('objection' in fact.lower() for fact in step['expected_facts']) for step in retention['steps'])


def test_new_sequence_fixture_triggers_the_required_summary_ci_job(tmp_path, monkeypatch):
    import subprocess
    import yaml
    workflow = yaml.safe_load((Path(__file__).parents[1] / '.github/workflows/evals.yml').read_text())
    script = workflow['jobs']['changes']['steps'][1]['run'].split("python - <<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    output = tmp_path / 'outputs'
    monkeypatch.setenv('EVENT', 'pull_request')
    monkeypatch.setenv('BASE', 'base')
    monkeypatch.setenv('HEAD', 'head')
    monkeypatch.setenv('GITHUB_OUTPUT', str(output))
    monkeypatch.setattr(subprocess, 'check_output', lambda *a, **kw: 'evals/summary_sequences.json\n')
    exec(compile(script, '<CI changes classifier>', 'exec'), {})
    assert dict(line.split('=') for line in output.read_text().splitlines()) == {'agent': 'false', 'summary': 'true'}


@pytest.mark.parametrize('fail_sequences', [False, True])
def test_live_runner_exit_and_artifacts_enforce_sequence_cohort(tmp_path, monkeypatch, fail_sequences):
    from types import SimpleNamespace
    import groq
    from src.services import conversation_summary
    def create(**kwargs):
        data = json.loads(kwargs['messages'][1]['content'])
        bad = fail_sequences and data['candidate'] in ['Candidate INV-SEQ-1', 'Candidate INV-SEQ-2']
        verdict = dict(GOOD, positive=False, coverage=2, reason='Lost prior fact') if bad else GOOD
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(verdict)))])
    monkeypatch.setenv('GROQ_API_KEY', 'synthetic-test-key')
    monkeypatch.setattr(groq, 'Groq', lambda **kwargs: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    monkeypatch.setattr(conversation_summary, '_call_model', lambda payload, **kwargs: 'Candidate ' + payload['invoice']['id'])
    assert summary.run('openai/gpt-oss-20b', 'qwen/qwen3.8-27b', tmp_path) == int(fail_sequences)
    report = json.loads((tmp_path / 'summary-latest.json').read_text())
    assert report['overall']['complete'] and report['suites']['sequence_steps']['cases'] == 31
    assert report['suites']['single']['passed']
    assert report['overall']['positive_rate'] >= .85
    assert report['overall']['passed'] is not fail_sequences
    assert report['production_incremental_refresh'] is False
    assert len(report['sequences_sha256']) == 64
    assert 'older-objection-eight-refreshes/eighth-refresh' in (tmp_path / 'summary-latest.md').read_text()
