"""Portable process memory limits for document parsers.

Call ``configure_process_limits`` as the first operation in a short-lived
extractor process, before importing document parsing libraries.
"""

from __future__ import annotations

import ctypes
import os
import sys

_JOB_HANDLE = None
_MEMORY_MONITOR = None


def configure_process_limits(memory_bytes: int = 512 * 1024 * 1024) -> None:
    if memory_bytes <= 0:
        raise ValueError("The process memory limit must be positive.")
    global _JOB_HANDLE
    if os.name == "nt":
        _JOB_HANDLE = _configure_windows_job(memory_bytes)
        return
    if sys.platform == "darwin":
        _configure_darwin_monitor(memory_bytes)
        return
    import resource

    for limit_name in ("RLIMIT_AS", "RLIMIT_DATA"):
        limit = getattr(resource, limit_name, None)
        if limit is None:
            continue
        resource.setrlimit(limit, (memory_bytes, memory_bytes))


def _configure_darwin_monitor(memory_bytes: int) -> None:
    """Watch RSS in a separate process: Darwin rejects RLIMIT_AS/DATA.

    Sampling can briefly overshoot the budget; this is not a kernel allocation
    cap. The independent process also works while a parser holds Python's GIL.
    Existing parent-side parser timeouts and input/output bounds still apply.
    """
    import select
    import subprocess

    global _MEMORY_MONITOR
    if _MEMORY_MONITOR is not None:
        raise RuntimeError("Parser memory supervision is already configured.")
    monitor = subprocess.Popen(
        [sys.executable, '-c',
         'from ien_contracts.process_limits import _darwin_watch_parent; '
         'import sys; _darwin_watch_parent(int(sys.argv[1]), int(sys.argv[2]))',
         str(os.getpid()), str(memory_bytes)],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, close_fds=True,
    )
    try:
        readable, _, _ = select.select([monitor.stdout], [], [], 5)
        if not readable or monitor.stdout.read(1) != b'1':
            raise RuntimeError("Could not start parser memory supervision.")
    except BaseException:
        monitor.kill()
        monitor.wait()
        raise
    finally:
        monitor.stdout.close()
    _MEMORY_MONITOR = monitor


def _darwin_watch_parent(parent_pid: int, memory_bytes: int) -> None:
    """Stop only our own parent if RSS exceeds the budget or monitoring fails."""
    import signal
    import time

    # rusage_info_v0, from the macOS SDK's sys/resource.h; sizes are bytes.
    class RUsageInfo(ctypes.Structure):
        _fields_ = [('uuid', ctypes.c_uint8 * 16)] + [
            (name, ctypes.c_uint64) for name in (
                'user_time', 'system_time', 'pkg_idle_wkups',
                'interrupt_wkups', 'pageins', 'wired_size', 'resident_size',
                'phys_footprint', 'proc_start_abstime', 'proc_exit_abstime',
            )
        ]

    library = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
    query = library.proc_pid_rusage
    query.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
    query.restype = ctypes.c_int
    info = RUsageInfo()
    if os.getppid() != parent_pid or query(parent_pid, 0, ctypes.byref(info)) != 0:
        return  # No handshake: the parser will refuse to start.
    sys.stdout.buffer.write(b'1')
    sys.stdout.buffer.flush()
    while os.getppid() == parent_pid:
        if query(parent_pid, 0, ctypes.byref(info)) != 0 or info.resident_size > memory_bytes:
            # Recheck parenthood before signalling: never target a reused PID.
            if os.getppid() == parent_pid:
                os.kill(parent_pid, signal.SIGKILL)
            return
        time.sleep(0.05)


def _configure_windows_job(memory_bytes: int):
    from ctypes import wintypes

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IoCounters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
        )]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimitInformation),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [wintypes.HANDLE, wintypes.INT, wintypes.LPVOID, wintypes.DWORD]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise OSError(ctypes.get_last_error(), "Could not create parser resource job.")
    limits = ExtendedLimitInformation()
    limits.BasicLimitInformation.LimitFlags = 0x100 | 0x2000  # process memory + kill on job close
    limits.ProcessMemoryLimit = memory_bytes
    if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        kernel32.CloseHandle(job)
        raise OSError(ctypes.get_last_error(), "Could not set parser memory limit.")
    if not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):
        kernel32.CloseHandle(job)
        raise OSError(ctypes.get_last_error(), "Could not isolate parser process.")
    return job
