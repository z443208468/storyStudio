"""Run original W10 oracles unchanged, with all writes owned by temporary roots."""
from pathlib import Path
import tempfile
from unittest.mock import patch

from tests import test_cnw_live_provider as old
from tests import test_p2_cost_guard as fees
from tools import cnw_live_provider as provider


class LegacyW10IsolatedTests(old.LiveProviderTransportTests):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='storystudio-w10-v1-compat-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        (self.base/'tests').mkdir()
        (self.base/'tools').mkdir()
        actual = Path(old.__file__).resolve().parents[1]
        for name in ('studio.ps1', 'cnw_w10_nk_live.ps1'):
            (self.base/'tools'/name).write_bytes((actual/'tools'/name).read_bytes())
        account = fees.CampaignLimitTests()
        account.setUp(); self.addCleanup(account.doCleanups)
        for binding in (patch.object(old, 'ROOT', self.base), patch.object(provider, 'ROOT', self.base)):
            binding.start(); self.addCleanup(binding.stop)
        super().setUp()
