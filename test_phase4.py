"""Phase 4 smoke test — run from project root: python test_phase4.py"""
import sys
sys.path.insert(0, '.')

errors = []

def check(label, fn):
    try:
        fn()
        print(f"  [PASS] {label}")
    except Exception as e:
        print(f"  [FAIL] {label}: {e}")
        errors.append(label)

print("\n=== Phase 4 Smoke Tests ===\n")

# 1. Imports
check("Import PatternInjector", lambda: __import__('autoheal.injector', fromlist=['PatternInjector']))
check("Import AutoHealAgent",   lambda: __import__('autoheal.agent',    fromlist=['AutoHealAgent']))
check("Import create_agent",    lambda: __import__('autoheal.agent',    fromlist=['create_agent']))
check("Package __init__ exports",lambda: __import__('autoheal',         fromlist=['PatternInjector','AutoHealAgent','create_agent']))

# 2. PatternInjector basic use
from autoheal.injector import PatternInjector, with_circuit_breaker, with_retry, with_timeout

inj = PatternInjector()
check("PatternInjector creation", lambda: None)

dummy = lambda: "hello"
wrapped = inj.inject("svc-cb", dummy, "circuit_breaker", {"failure_threshold": 3})
check("inject circuit_breaker + call", lambda: wrapped())

wrapped2 = inj.inject("svc-retry", dummy, "retry", {"max_attempts": 2})
check("inject retry + call", lambda: wrapped2())

wrapped3 = inj.inject("svc-timeout", dummy, "timeout", {"max_seconds": 5.0})
check("inject timeout + call", lambda: wrapped3())

check("active_count == 3", lambda: (lambda c: None if c == 3 else (_ for _ in ()).throw(AssertionError(f"expected 3, got {c}")))(inj.active_count()))

inj.remove("svc-cb")
check("remove pattern", lambda: (lambda c: None if c == 2 else (_ for _ in ()).throw(AssertionError(f"expected 2, got {c}")))(inj.active_count()))

s = inj.summary()
check("injector.summary() has keys", lambda: (s["active_injections"], s["total_injections"], s["services"]))

# 3. Decorator API
@with_circuit_breaker(failure_threshold=3)
def api1(): return "ok"
check("@with_circuit_breaker decorator", lambda: api1())

@with_retry(max_attempts=2)
def api2(): return "ok"
check("@with_retry decorator", lambda: api2())

@with_timeout(max_seconds=3.0)
def api3(): return "ok"
check("@with_timeout decorator", lambda: api3())

# 4. Agent
from autoheal.monitor import _monitor
from autoheal.agent import create_agent

agent = create_agent(_monitor, scan_interval=2)
check("create_agent()", lambda: None)
check("agent.is_running == False before start", lambda: None if not agent.is_running else (_ for _ in ()).throw(AssertionError("should not be running yet")))

agent.start()
import time; time.sleep(0.5)
check("agent.is_running == True after start", lambda: None if agent.is_running else (_ for _ in ()).throw(AssertionError("should be running")))
check("agent uptime > 0", lambda: None if agent.uptime_seconds > 0 else (_ for _ in ()).throw(AssertionError("uptime 0")))

agent.stop()
check("agent.is_running == False after stop", lambda: None if not agent.is_running else (_ for _ in ()).throw(AssertionError("should have stopped")))

print()
if errors:
    print(f"=== FAILED: {len(errors)} test(s): {errors} ===")
    sys.exit(1)
else:
    print(f"=== ALL TESTS PASSED ===\n")
