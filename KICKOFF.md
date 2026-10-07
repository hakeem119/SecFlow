# Kickoff checklist (in order)
1. Push the REAL project (main after Phase 3) to GitHub. .gitignore: .venv, .coverage, __pycache__.
2. Protect main: PR required, CI green, no force-push, CODEOWNERS review.
3. Merge the starter kit (this folder) via an M3 PR: AGENTS modes section, .agent/rules,
   CODEOWNERS (fill handles), scripts/check_ownership.py.
4. Make sure AGENTS.md in the repo has D1-D14, W1-W6 (the old zip does not).
5. Each member: own branch + own git worktree (m1/phase-4-git, m2/tool-runner, m3/snapshot-builder).
6. Round 1 (plans only): run the 3 prompts, each produces docs/plans/<id>-plan.md. Review all 3 together.
7. Day-0 contract PRs, in this order: M2 CommandRunner+Fake -> M1 ports -> M3 sample_snapshot.yaml+fixtures.
   After merge: contracts FROZEN.
8. Round 2: implementation per the PR breakdown in each plan, DEV MODE (no new tests).
9. Merge order: M2 contract -> M1 git -> M2 runner -> scc -> Syft -> Semgrep -> M3 snapshot builder.
10. M3 wires RepositoryAnalysisService (fakes first, then real tools in Docker).
11. Switch to VERIFY MODE: write tests, 100% coverage, full gate + Docker build.
