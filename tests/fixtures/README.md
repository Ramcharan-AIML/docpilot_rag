# CI fixture corpus: `corpus/ci_fixture/` (step 2.10)

Seven short pages about **Lumen**, a task-queue library that does not exist. We wrote them
ourselves for the CI eval gate, so there is no licence question (own work, same terms as
this repository) and nothing to download in CI. The questions are in
`evals/golden/ci.jsonl`; the gate is explained in `docs/teaching/primer_ci_eval_gate.md`.

Pages cover prose, code blocks, a settings table, an error-code table and exact
identifiers. Several pages talk about retries, timeouts and workers on purpose: those
"distractors" make ranking matter, so a broken pipeline loses points.

Changing a page changes the gate's scores: re-make the baseline in the same pull request
and say why (see the primer).
