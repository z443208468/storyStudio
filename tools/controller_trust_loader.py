"""Read-only loading of one independently deployed, self-contained verifier.

This is a provenance boundary, not a Python sandbox or a trust-root installer.
The first interface deliberately has no deployment imports or dynamic plugins.
"""
from __future__ import annotations

import ast
import builtins
import ctypes
from ctypes import wintypes
from contextlib import contextmanager
import os
from pathlib import Path
import uuid

try:
    from .cnw_contract import ContractError
    from .project_paths import _assert_no_reparse
except ImportError:
    from cnw_contract import ContractError
    from project_paths import _assert_no_reparse


def _pending(reason: str):
    raise ContractError("W10_ATTESTATION_PENDING", reason)


def _fixed_deployment_file() -> Path:
    if os.name != "nt":
        _pending("protected Windows deployment is not available on this platform")
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    ole = ctypes.WinDLL("ole32", use_last_error=True)
    shell.SHGetKnownFolderPath.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.HANDLE,
                                          ctypes.POINTER(ctypes.c_void_p)]
    shell.SHGetKnownFolderPath.restype = ctypes.c_long
    ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    ole.CoTaskMemFree.restype = None
    folder_id = ctypes.create_string_buffer(uuid.UUID("905e63b6-c1bf-494e-b29c-65b732d3d21a").bytes_le)
    allocated = ctypes.c_void_p()
    if shell.SHGetKnownFolderPath(folder_id, 0, None, ctypes.byref(allocated)) != 0:
        _pending("ProgramFiles known folder could not be resolved")
    try:
        root = Path(ctypes.wstring_at(allocated))
    finally:
        ole.CoTaskMemFree(allocated)
    if not root.is_absolute():
        _pending("ProgramFiles known folder is not absolute")
    return root / "StoryStudioControllerTrust" / "controller_attestations.py"


def _token_security_snapshot(path: Path, handle, *, thread: bool) -> bytes:
    """Reject effective Writer write/replace/ownership rights without changing ACLs."""
    if os.name != "nt":
        _pending("effective Windows token security cannot be inspected")
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    ptr = ctypes.c_void_p
    dword_ptr = ctypes.POINTER(wintypes.DWORD)
    kernel.GetCurrentThread.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ptr]
    kernel.LocalFree.restype = ptr
    adv.OpenThreadToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, ctypes.POINTER(wintypes.HANDLE)]
    adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    adv.DuplicateToken.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.POINTER(wintypes.HANDLE)]
    adv.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ptr, wintypes.DWORD, dword_ptr]
    adv.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ptr]
    adv.EqualSid.argtypes = [ptr, ptr]
    adv.CheckTokenMembership.argtypes = [wintypes.HANDLE, ptr, ctypes.POINTER(wintypes.BOOL)]
    adv.GetSecurityInfo.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.DWORD,
        ctypes.POINTER(ptr), ctypes.POINTER(ptr), ctypes.POINTER(ptr), ctypes.POINTER(ptr), ctypes.POINTER(ptr)]
    adv.GetSecurityInfo.restype = wintypes.DWORD
    adv.GetSecurityDescriptorLength.argtypes = [ptr]
    adv.GetSecurityDescriptorLength.restype = wintypes.DWORD
    class GenericMapping(ctypes.Structure):
        _fields_ = [(name, wintypes.DWORD) for name in ("read", "write", "execute", "all")]
    adv.AccessCheck.argtypes = [ptr, wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(GenericMapping),
                               ptr, dword_ptr, dword_ptr, ctypes.POINTER(wintypes.BOOL)]
    for name in ("OpenThreadToken", "OpenProcessToken", "DuplicateToken", "GetTokenInformation",
                 "LookupPrivilegeValueW", "EqualSid", "CheckTokenMembership", "AccessCheck"):
        getattr(adv, name).restype = wintypes.BOOL
    original = wintypes.HANDLE()
    effective = wintypes.HANDLE()
    descriptor = ptr()
    # A restricted thread cannot hide the process's ability to revert to its
    # broader identity. Both contexts must pass; query failure is never fallback.
    if thread:
        if not adv.OpenThreadToken(kernel.GetCurrentThread(), 0x000A, False, ctypes.byref(original)):
            if ctypes.get_last_error() == 1008:
                return b"NO_THREAD_IMPERSONATION"
            _pending("effective thread token could not be queried")
    elif not adv.OpenProcessToken(kernel.GetCurrentProcess(), 0x000A, ctypes.byref(original)):
        _pending("process token could not be queried")
    try:
        if not adv.DuplicateToken(original, 2, ctypes.byref(effective)):
            _pending("effective impersonation token could not be created for AccessCheck")
        def token_info(kind):
            size = wintypes.DWORD()
            adv.GetTokenInformation(effective, kind, None, 0, ctypes.byref(size))
            if not size.value:
                _pending("token information size is unavailable")
            buffer = ctypes.create_string_buffer(size.value)
            if not adv.GetTokenInformation(effective, kind, buffer, size, ctypes.byref(size)):
                _pending("token information could not be queried")
            return buffer
        privileges = token_info(3)  # TOKEN_PRIVILEGES
        count = int.from_bytes(privileges.raw[:4], "little")
        # Disabled privileges are still held and can be enabled by their owner.
        for name in ("SeTakeOwnershipPrivilege", "SeRestorePrivilege", "SeDebugPrivilege",
                     "SeTcbPrivilege", "SeCreateTokenPrivilege", "SeImpersonatePrivilege"):
            luid = ctypes.create_string_buffer(8)
            if not adv.LookupPrivilegeValueW(None, name, luid):
                _pending("security privilege identity could not be resolved")
            if any(privileges.raw[4 + index * 12:12 + index * 12] == luid.raw for index in range(count)):
                _pending("Writer token holds a privilege capable of bypassing deployment isolation")
        owner, group, dacl = ptr(), ptr(), ptr()
        if adv.GetSecurityInfo(handle, 1, 7, ctypes.byref(owner), ctypes.byref(group),
                                    ctypes.byref(dacl), None, ctypes.byref(descriptor)):
            _pending("deployment security descriptor could not be read")
        if not descriptor.value or not owner.value or not group.value or not dacl.value:
            _pending("deployment has a missing owner/group or NULL DACL")
        user = token_info(1)  # TOKEN_USER begins with SID_AND_ATTRIBUTES.
        user_sid = ptr.from_buffer(user).value
        membership = wintypes.BOOL()
        if not adv.CheckTokenMembership(effective, owner, ctypes.byref(membership)):
            _pending("deployment owner membership could not be checked")
        if adv.EqualSid(owner, user_sid) or membership.value:
            _pending("Writer owns deployment code or a containing directory")
        mapping = GenericMapping(0x120089, 0x120116, 0x1200A0, 0x1F01FF)
        # Check each dangerous right individually; rejecting one combined request
        # would not prove denial of every member of that request.
        rights = [0x0002, 0x0004, 0x0010, 0x0100, 0x10000, 0x40000, 0x80000]
        if _held_file_identity(handle)[-1] & 0x10:
            rights.append(0x0040)  # FILE_DELETE_CHILD permits replacing a protected file.
        for desired in rights:
            used = ctypes.create_string_buffer(4096)
            used_size = wintypes.DWORD(len(used))
            granted = wintypes.DWORD()
            allowed = wintypes.BOOL()
            if not adv.AccessCheck(descriptor, effective, desired, ctypes.byref(mapping), used,
                                   ctypes.byref(used_size), ctypes.byref(granted), ctypes.byref(allowed)):
                _pending("effective deployment access could not be determined")
            if allowed.value or granted.value & desired:
                _pending("Writer can modify or replace deployment code or its containing directory")
        size = adv.GetSecurityDescriptorLength(descriptor)
        if not size:
            _pending("deployment security descriptor length is unavailable")
        return ctypes.string_at(descriptor, size)
    finally:
        if descriptor.value:
            kernel.LocalFree(descriptor)
        if effective.value:
            kernel.CloseHandle(effective)
        kernel.CloseHandle(original)


def _windows_security_snapshot(path: Path, handle) -> tuple:
    return (_token_security_snapshot(path, handle, thread=False),
            _token_security_snapshot(path, handle, thread=True))


def _kernel_file_api():
    if os.name != "nt":
        _pending("protected file handles require Windows")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    kernel.GetFileInformationByHandle.restype = wintypes.BOOL
    kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    kernel.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    kernel.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                               ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    kernel.ReadFile.restype = wintypes.BOOL
    return kernel


def _held_file_identity(handle) -> tuple:
    class FileInformation(ctypes.Structure):
        _fields_ = [("attributes", wintypes.DWORD), ("creation", wintypes.FILETIME),
            ("access", wintypes.FILETIME), ("write", wintypes.FILETIME), ("volume", wintypes.DWORD),
            ("size_high", wintypes.DWORD), ("size_low", wintypes.DWORD), ("links", wintypes.DWORD),
            ("index_high", wintypes.DWORD), ("index_low", wintypes.DWORD)]
    info = FileInformation()
    if not _kernel_file_api().GetFileInformationByHandle(handle, ctypes.byref(info)):
        _pending("held deployment file identity could not be read")
    if info.attributes & 0x400:
        _pending("held deployment object is a reparse point")
    return (info.volume, info.index_high, info.index_low, info.size_high, info.size_low,
            info.write.dwHighDateTime, info.write.dwLowDateTime, info.attributes)


@contextmanager
def _hold_deployment(path: Path):
    """Keep all path objects open without write/delete sharing through factory."""
    kernel = _kernel_file_api()
    held = {}
    try:
        for component in (*reversed(path.parents), path):
            _assert_no_reparse(component, code="W10_ATTESTATION_PENDING")
            desired = 0x20000 | (1 if component == path else 0)  # READ_CONTROL and file data
            handle = kernel.CreateFileW(str(component), desired, 1, None, 3,
                                        0x02000000 | 0x00200000, None)
            if handle == ctypes.c_void_p(-1).value or not handle:
                _pending("deployment objects could not be held against replacement")
            held[component] = handle
            attributes = _held_file_identity(handle)[-1]
            if bool(attributes & 0x10) != (component != path):
                _pending("held deployment object has an unexpected file/directory type")
            buffer = ctypes.create_unicode_buffer(32768)
            length = kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
            if not length or length >= len(buffer):
                _pending("held deployment path could not be established")
            final = buffer.value
            if final.startswith("\\\\?\\"):
                final = final[4:]
            if os.path.normcase(final.rstrip("\\")) != os.path.normcase(str(component).rstrip("\\")):
                _pending("held deployment object differs from its fixed path")
        yield held
    finally:
        for handle in reversed(list(held.values())):
            kernel.CloseHandle(handle)


def _read_held_source(handle) -> bytes:
    kernel = _kernel_file_api()
    result = bytearray()
    while True:
        buffer = ctypes.create_string_buffer(65536)
        count = wintypes.DWORD()
        if not kernel.ReadFile(handle, buffer, len(buffer), ctypes.byref(count), None):
            _pending("held deployment bytes could not be read")
        if not count.value:
            return bytes(result)
        result.extend(buffer.raw[:count.value])
        if len(result) > 512 * 1024:
            _pending("fixed deployment verifier exceeds the supported source size")


def _protected_snapshot(path: Path, held) -> tuple:
    _assert_no_reparse(path, code="W10_ATTESTATION_PENDING")
    if not path.is_file():
        _pending("fixed independent verifier deployment is absent")
    return tuple((str(component), _held_file_identity(handle), _windows_security_snapshot(component, handle))
                 for component, handle in held.items())


def load_deployment_verifier():
    """No import search, cache reuse, environment roots or deployment writes."""
    try:
        path = _fixed_deployment_file()
        with _hold_deployment(path) as held:
            before = _protected_snapshot(path, held)
            raw = _read_held_source(held[path])
            return _execute_verified_source(path, raw, held, before)
    except ContractError:
        raise
    except Exception as exc:
        raise ContractError("W10_ATTESTATION_PENDING", "independent deployment could not be safely loaded") from exc


def _execute_verified_source(path: Path, raw: bytes, held, before):
    tree = ast.parse(raw, filename=str(path))
    # Explicitly no dependencies in this first fixed-file protocol. Public
    # trust material must be embedded in the protected file. This check also
    # rejects imports deferred to factory/verify before any module code runs.
    if any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree)):
        _pending("deployment verifier requires dependencies not supported by this fixed-file interface")
    code = compile(tree, str(path), "exec")
    if _protected_snapshot(path, held) != before:
        _pending("deployment path, identity or effective permissions changed before execution")
    names = ("__build_class__", "object", "type", "bytes", "bytearray", "str", "int", "bool",
             "dict", "list", "tuple", "set", "frozenset", "len", "range", "enumerate", "zip",
             "isinstance", "issubclass", "pow", "min", "max", "sum", "all", "any", "ord", "chr",
             "Exception", "ValueError", "TypeError", "RuntimeError", "staticmethod", "classmethod", "property")
    def reject_import(*args, **kwargs):
        _pending("deployment verifier attempted an unsupported dynamic dependency")
    allowed = {name: getattr(builtins, name) for name in names}
    allowed["__import__"] = reject_import
    namespace = {"__name__": "_storystudio_fixed_controller_verifier", "__builtins__": allowed}
    exec(code, namespace)
    factory = namespace.get("get_controller_attestation_verifier")
    if not callable(factory):
        _pending("fixed deployment has no verifier factory")
    verifier = factory()
    if verifier is None or not callable(getattr(verifier, "verify", None)):
        _pending("fixed deployment returned no verifier")
    return verifier
