# Independent Verification History

## Candidate 1: rejected

- Verdict: `PRE_FREEZE_REJECTED`
- Base HEAD: `59b94b9ecc089c3dca96856077559a4efca35566`
- Graph at review: `c97fb06942ecfef1ed3a7f47bd54a5b59572beb302275a52be8bf63f91f2b2b2`
- Report SHA-256: `35106382195a87d8f7ec753e52477f54d536478e97f8af08e7683051823066c9`
- Structured verdict SHA-256: `57687857bf2af350b08697c67e0da26b538d97d9bef411a0aad12577f63fc9b5`

Blocking findings were universal dual-review taskcards, seven-first and stale timing text, six
campaigns existing only in prose, an extra Python full-suite gate, and evidence that claimed those
defects were already removed.

## Repair disposition

The defects were repaired in their owning graph, schema, controller, master, requirements, and
evidence surfaces. No finding was waived. The same independent lane was asked to overwrite its
canonical report and structured verdict after rechecking the current candidate.

## Candidate 2: rejected

- Verdict: `PRE_FREEZE_REJECTED`
- Graph at review: `e962438f5d384c976005a48ef367889780719b14bec3f3d031acdbf2ffcad9ce`
- Report SHA-256: `54a17f2153758dab6977d27ec91905361415b43a1541e2ea9241e87163e3ca0c`
- Structured verdict SHA-256: `c968d5cdea5a217e40ac2580df9ccbf22f85756f0fb56f22afaf5976f6d0f38d`

The second review confirmed all first-round structural fixes, then found a remaining readiness-versus-Note
ordering conflict, a stale generated status snapshot, one seven-representative concurrency sentence,
an obsolete trusted/full-suite verification checklist, and one formatting defect. These were repaired
in their owning graph, generated status, master Architecture, master Verification Checklist, and tests.

## Candidate 3: rejected

- Verdict: `PRE_FREEZE_REJECTED`
- Graph at review: `ab5235a176a375bca334625147140c934c33a9cd3bcfdc33dbca874664770943`
- Report SHA-256: `9e754287fd3efae95ce4a2c810f07f27351757ad6fecee55976ebd42f2c79083`
- Structured verdict SHA-256: `01c1c3ef904e05a6ecc45d79c0b0c4f255d5b28f2755443c68abb83ee926e060`

The third review confirmed every candidate-2 repair, then found two remaining statements in
`plans/idea.md` and the readiness task objective that still implied Note completed first. Both now
state that zero-call readiness freezes .NET/Java selections before Note and the two selected slices
execute together.

## Candidate 4: accepted

- Verdict: `PRE_FREEZE_ACCEPTED`
- Graph at review: `37e33944e5d99ca32897c2a23dcf7e882f14ccb3d4a37c5edc510d99c9231ae3`
- Durable state: v698; 506 preserved transitions; graph drift false
- Report SHA-256: `83924cba33a4ced22981fd80d9a7602edb4db3170f32819386dfd234cfcce672`
- Structured verdict SHA-256: `7f2901ae314aa0508e851e40080381f836914d025623cd0e1bc90d6633990bda`

The final independent review found no remaining material plan contradiction and explicitly allowed
`CampaignFreezeV1` creation.
