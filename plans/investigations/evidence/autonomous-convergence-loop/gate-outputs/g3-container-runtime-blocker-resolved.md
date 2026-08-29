# G3 — container-runtime blocker: diagnosed and resolved locally, not escalated

The first `L8-PF-02` canary run failed:

```
aspose-3d-foss/Aspose.3D-FOSS-for-Python: BOUNDED_VERIFIED_CANARY
registry-heal: NO_DRIFT
aspose-3d-foss/Aspose.3D-FOSS-for-Python: MISSION_BOUND -- immediate_goal=DELIVERY-FIRST-COMPLETE-CANDIDATE
error: container registry acquisition remained unavailable after bounded retry
aspose-3d-foss/Aspose.3D-FOSS-for-Python: intake READY_FAST_PATH at d9f3bfe50d47e8156266955dda52ec5abf2d9dec (executed)
EXIT=3
```

## Attempt 1 — diagnosis

`docker version` failed with
`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`, and no
`docker` process was running. Docker Desktop was installed at the default path but its daemon was
not started. Decision #89 requires toolchains to be provisioned "autonomously in disposable
isolated environments", so the isolated executor needs a live container runtime; without one, the
acquisition/verification stage cannot run and the transaction stops before producing a candidate.

## Attempt 2 — repair, not escalation

Started Docker Desktop and confirmed the daemon: `docker version` reports server `28.4.0`.
`plans/GOVERNANCE.md` rule 19 grants standing authority for "isolated Docker/`act` work at the
appropriate gate" and process management, so this needed no separate approval.

This is recorded deliberately: it is exactly the class of failure that gets mislabelled a "true
external blocker" when it is really an unstarted local service. The blocker standard requires
repository-local repair to be exhausted first, and here the first repair attempt resolved it.

## Result

The re-run proceeds past container acquisition. Its outcome is recorded in
`g4-pf02-canary-outcome.md`.
