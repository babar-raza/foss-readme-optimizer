# Local Heterogeneous Qualification Proof

This bundle proves task `L8-LOCAL-HETEROGENEOUS-QUALIFICATION` against immutable source commit
`d30a811cc414cc71a83f9a09cb345821a0fe14c2`.

The live campaign ran from the detached, branchless worktree
`runs/qualification-source-d30a811`, not from the concurrently editable `main` checkout.
`campaign-source.json` binds the prompts, planner and reviewer corpora, harnesses, qualification
logic, and forced-tool reviewer client to their SHA-256 hashes. The detached worktree was clean
before and after every session.

Acceptance results:

- three independent live sessions and 159 governed evaluations;
- planner route: 51/51 (100%);
- independent README-review route: 106/108 (98.15%);
- overall: 157/159 (98.74%);
- every required volume and pass-rate gate is true;
- no route was disabled;
- 53/53 deterministic heterogeneous, repair, no-op, resume, factuality, protected-content,
  source-build, multi-root, and prompt-injection controls passed.

The two misses were conservative false rejections of the otherwise grounded
`cpp_specific_grounded_candidate` in sessions two and three. They were not false accepts and do
not conceal a factuality or safety failure. They remain visible in
`agentic-qualification-summary.json`; the C++ route score is 13/15 (86.67%) as a per-ecosystem
diagnostic, while the governed model-route acceptance is 106/108 (98.15%). The required overall
and per-route floor is 95%, not a per-ecosystem minimum.

An earlier campaign run directly from `main` passed numerically but was rejected as acceptance
evidence after its recorded source fingerprint disagreed with the bound commit during concurrent
editing. It remains only under `runs/`; this bundle contains only the isolated-worktree rerun.

`independent-implementation-review.md` records the evidence review and closure verdict.
`sha256sums.txt` covers every file in this directory other than itself.
