"""Real PowerShell routing without manual inputs, ending at unavailable trust.

Python CLI positive execution is covered separately with the owned simulator.
No test verifier is installed into the actual application subprocess.
"""
import os
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from tests import test_cnw_live_authorization as grants
from tools import cost_guard


class W10PowerShellRoutingTests(unittest.TestCase):
    def test_real_v2_prepare_and_execute_reach_authorization_without_manual_packets(self):
        owner = grants.LiveAuthorizationTests()
        owner.setUp(); self.addCleanup(owner.doCleanups)
        owner.sign(terms=owner.full_terms()); owner.create()
        before = (owner.run/'run_state.json').read_bytes()
        script = Path(__file__).resolve().parents[1]/'tools/studio.ps1'
        executable = shutil.which('pwsh')
        self.assertIsNotNone(executable, 'real PowerShell runtime is required for this route evidence')
        env = {k: v for k, v in os.environ.items() if 'API_KEY' not in k and not k.startswith('STORYSTUDIO_')}
        observed = []
        for action in ('prepare-live', 'live-call'):
            argv = [executable, '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                '-File', str(script), action, '-ProjectRoot', str(owner.root), '-RunId', owner.run_id, '-Stage', 'plot']
            result = subprocess.run(argv, env=env, capture_output=True, timeout=60)
            stdout = result.stdout.decode('utf-8', errors='replace')
            stderr = result.stderr.decode('utf-8', errors='replace')
            text = stdout + stderr
            record = {'argv': argv, 'exit_code': result.returncode, 'stdout': stdout, 'stderr': stderr,
                      'stdout_bytes_hex': result.stdout.hex(), 'stderr_bytes_hex': result.stderr.hex()}
            destination = os.environ.get('CNW_LIVE_GRANT_TEST_EVIDENCE')
            if destination:
                Path(destination+'.powershell.'+action+'.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('PREPARE_LIVE_ROLE_REQUIRES_INPUT_MAP', text)
            self.assertNotIn('LIVE_CALL_REQUIRES_RUN_STAGE_PACKET', text)
            self.assertNotIn('LIVE_ROLE_PACKET_ARGUMENTS_REQUIRED', text)
            self.assertIn('CNW_LIVE_EXECUTION_FAILED', text)
            self.assertTrue(any(code in text for code in ('CONTROLLER_TRUST', 'ATTESTATION', 'LIVE_AUTHORIZATION')),
                            'the real route must reach its authorization gate: '+text)
            observed.append(record)
        self.assertEqual(before, (owner.run/'run_state.json').read_bytes())
        self.assertFalse(cost_guard.accounting.LEDGER.exists())
        print({'scope': 'REAL_POWERSHELL_AUTHORIZATION_BOUNDARY_NOT_POSITIVE_PROVIDER_EXECUTION',
               'provider_calls': 0, 'routes': observed})
