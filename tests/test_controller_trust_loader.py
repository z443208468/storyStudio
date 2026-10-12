"""Loader provenance negatives; simulated deployment is never production trust."""
import builtins
from contextlib import contextmanager
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools import controller_trust_loader as loader
from tools.cnw_contract import ContractError


STANDALONE = b'''class MockOnlyVerifier:
    def verify(self, signer_id, message, signature):
        return signer_id == "MOCK_ONLY" and signature == b"SIMULATED" and message == b"fixture"
def get_controller_attestation_verifier():
    return MockOnlyVerifier()
'''


class FixedControllerLoaderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="controller-protocol-fictional-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "controller_attestations.py"
        self.source.write_bytes(STANDALONE)
        self.native_hold = loader._hold_deployment
        self.native_identity = loader._held_file_identity
        @contextmanager
        def simulated_hold(path):
            yield {component: component for component in (*reversed(path.parents), path)}
        for name, replacement in (("_hold_deployment", simulated_hold),
                ("_read_held_source", lambda path: path.read_bytes()),
                ("_held_file_identity", lambda path: (path.stat().st_ino, path.stat().st_size, path.stat().st_mtime_ns))):
            substitute = patch.object(loader, name, replacement)
            substitute.start()
            self.addCleanup(substitute.stop)

    def test_simulated_protected_file_consumes_protocol_without_import_search(self):
        impostor = SimpleNamespace(get_controller_attestation_verifier=lambda: self.fail("cached impostor executed"))
        with patch.object(loader, "_fixed_deployment_file", return_value=self.source), \
             patch.object(loader, "_windows_security_snapshot", return_value=b"SIMULATED_PROTECTED_ACL"), \
             patch.dict(sys.modules, {"storystudio_deployment_trust.controller_attestations": impostor}), \
             patch.dict(os.environ, {"PYTHONPATH": str(self.root), "ProgramFiles": str(self.root)}):
            verifier = loader.load_deployment_verifier()
        self.assertIs(verifier.verify("MOCK_ONLY", b"fixture", b"SIMULATED"), True)
        self.assertIs(verifier.verify("OTHER", b"fixture", b"SIMULATED"), False)

    def test_missing_acl_null_dacl_owner_and_parent_write_fail_before_execution(self):
        for reason in ("ACL_QUERY_FAILED", "NULL_DACL", "WRITER_OWNER", "WRITER_WRITE", "PARENT_DELETE_CHILD"):
            with self.subTest(reason=reason), \
                 patch.object(loader, "_fixed_deployment_file", return_value=self.source), \
                 patch.object(loader, "_windows_security_snapshot", side_effect=ContractError("W10_ATTESTATION_PENDING", reason)), \
                 patch.object(loader, "exec", wraps=builtins.exec, create=True) as execute:
                with self.assertRaisesRegex(ContractError, "W10_ATTESTATION_PENDING"):
                    loader.load_deployment_verifier()
                execute.assert_not_called()
        with patch.object(loader, "_fixed_deployment_file", return_value=self.root / "missing.py"), \
             patch.object(loader, "exec", wraps=builtins.exec, create=True) as execute:
            with self.assertRaisesRegex(ContractError, "W10_ATTESTATION_PENDING"):
                loader.load_deployment_verifier()
            execute.assert_not_called()

    def test_transitive_parent_and_delayed_imports_reject_before_any_module_execution(self):
        for dependency in (b"import os\n", b"from package import child\n",
                b"def unused_factory():\n    import innocent_stdlib\n",
                b"class Extra:\n    def verify(self, *args):\n        import late_dependency\n"):
            self.source.write_bytes(dependency + STANDALONE)
            with self.subTest(dependency=dependency.decode()), \
                 patch.object(loader, "_fixed_deployment_file", return_value=self.source), \
                 patch.object(loader, "_windows_security_snapshot", return_value=b"SIMULATED_PROTECTED_ACL"), \
                 patch.object(loader, "exec", wraps=builtins.exec, create=True) as execute:
                with self.assertRaisesRegex(ContractError, "W10_ATTESTATION_PENDING"):
                    loader.load_deployment_verifier()
                execute.assert_not_called()

    def test_dynamic_import_during_verify_remains_blocked_after_factory_returns(self):
        self.source.write_bytes(b'''class Verifier:
    def verify(self, *args):
        return __import__("writer_controlled_dependency")
def get_controller_attestation_verifier():
    return Verifier()
''')
        with patch.object(loader, "_fixed_deployment_file", return_value=self.source), \
             patch.object(loader, "_windows_security_snapshot", return_value=b"SIMULATED_PROTECTED_ACL"):
            verifier = loader.load_deployment_verifier()
        with self.assertRaisesRegex(ContractError, "W10_ATTESTATION_PENDING"):
            verifier.verify("MOCK_ONLY", b"fixture", b"SIMULATED")

    def test_path_identity_and_permissions_changes_reject_before_execution(self):
        snapshot = loader._protected_snapshot
        checks = []
        def changed(path, held):
            value = snapshot(path, held)
            checks.append(value)
            if len(checks) == 2:
                return (*value, (("SIMULATED_CHANGED_ACL", b"OTHER"),))
            return value
        with patch.object(loader, "_fixed_deployment_file", return_value=self.source), \
             patch.object(loader, "_windows_security_snapshot", return_value=b"SIMULATED_PROTECTED_ACL"), \
             patch.object(loader, "_protected_snapshot", side_effect=changed), \
             patch.object(loader, "exec", wraps=builtins.exec, create=True) as execute:
            with self.assertRaisesRegex(ContractError, "W10_ATTESTATION_PENDING"):
                loader.load_deployment_verifier()
            execute.assert_not_called()

    def test_real_writer_owned_temp_and_environment_roots_cannot_supply_trust(self):
        if os.name == "nt":
            with patch.object(loader, "_held_file_identity", self.native_identity), \
                 self.assertRaisesRegex(ContractError, "W10_ATTESTATION_PENDING"):
                with self.native_hold(self.source) as held:
                    loader._windows_security_snapshot(self.source, held[self.source])
            original = loader._fixed_deployment_file()
            with patch.dict(os.environ, {"ProgramFiles": str(self.root), "PROGRAMFILES": str(self.root),
                    "PYTHONPATH": str(self.root), "STORYSTUDIO_DATA_HOME": str(self.root)}):
                self.assertEqual(loader._fixed_deployment_file(), original)
            self.assertFalse(original.is_relative_to(self.root))

    def test_restricted_thread_cannot_hide_process_write_or_restore_privilege(self):
        def token_check(path, handle, *, thread):
            if not thread:
                raise ContractError("W10_ATTESTATION_PENDING", "SIMULATED_PROCESS_RESTORE_PRIVILEGE")
            return b"SIMULATED_RESTRICTED_THREAD"
        with patch.object(loader, "_fixed_deployment_file", return_value=self.source), \
             patch.object(loader, "_token_security_snapshot", side_effect=token_check) as check, \
             patch.object(loader, "exec", wraps=builtins.exec, create=True) as execute:
            with self.assertRaisesRegex(ContractError, "PROCESS_RESTORE"):
                loader.load_deployment_verifier()
            self.assertIs(check.call_args.kwargs["thread"], False)
            execute.assert_not_called()

    def test_handle_open_read_and_ancestor_identity_failure_stop_execution(self):
        for operation in ("_hold_deployment", "_read_held_source", "_held_file_identity"):
            with self.subTest(operation=operation), \
                 patch.object(loader, "_fixed_deployment_file", return_value=self.source), \
                 patch.object(loader, operation, side_effect=OSError("SIMULATED_HANDLE_FAILURE")), \
                 patch.object(loader, "_windows_security_snapshot", return_value=b"SIMULATED_PROTECTED_ACL"), \
                 patch.object(loader, "exec", wraps=builtins.exec, create=True) as execute:
                with self.assertRaisesRegex(ContractError, "W10_ATTESTATION_PENDING"):
                    loader.load_deployment_verifier()
                execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
