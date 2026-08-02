# Campaign Freeze Validation History

## Freeze candidate 1: rejected

- Verdict: `FREEZE_REJECTED`
- Control commit: `83d43102582c4cf7d74250529927b2256e30f718`
- Graph: `37e33944e5d99ca32897c2a23dcf7e882f14ccb3d4a37c5edc510d99c9231ae3`
- Independent report SHA-256: `1c520e6b4184acdfeb0a852fab5a5330a85284cd42bd3c349d8f80cac9bf77c5`
- Independent structured verdict SHA-256: `45b3b34adbb311f0c0bd3f92214687cadfae7ac5aedcfcaa083a05c6f6babc9a`

Nine of eleven dependency groups and all seven critical files reproduced. The `validators` and
`independent_review` hashes used precise predicate-based membership, but the manifest described
those sets with ambiguous glob-like strings. The independent verifier reasonably interpreted the
strings differently and rejected the freeze. The manifest now states the exact path and basename
predicates used by the hash algorithm; no dependency bytes or expected hashes were changed.

## Freeze candidate 2: accepted

- Verdict: `FREEZE_ACCEPTED`
- Manifest SHA-256: `1af5a04a5af2105c8e87bf8e1c60e048f83d722092b5affee3f76cc68675a5c2`
- Independent report SHA-256: `914c966d57c4bf4753299a479caedb81379a2b54d075d9d7ab2d2a4824e308ac`
- Independent structured verdict SHA-256: `0b3662120c54553a031614b864e8b930322646e1a1995d8052d2cb275fb7fa80`
- Dependency groups: 11/11 reproduced
- Critical files: 7/7 reproduced
- ZIP creation: authorized

The accepted check used the manifest's exact selection predicates. No expected dependency digest
was waived or changed after the rejected attempt.
