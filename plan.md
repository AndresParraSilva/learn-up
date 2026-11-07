# Dependency security audit plan

- [x] Review project instructions, working tree, dependency manifests, environments, and prior audit results.
- [x] Investigate the local crap4py package, which pip-audit could not match to PyPI; determine its provenance and whether it has applicable advisories. The remaining audited uv environment and npm dependencies had no known findings in the previous pass.
- [x] If this project uses Node.js, inventory its runtime declarations and environments. Require Node 22 or newer; update Node 22 to at least 22.23.4, Node 24 to at least 24.22.1, and Node 26 to at least 26.12.1. Verify compatibility and the project’s build and tests after updates.
- [x] Apply only compatible fixes that preserve functionality; record advisory IDs, versions, dependency paths, and any findings that cannot be safely fixed.
- [x] Repeat the applicable audits and run the project’s tests or build; document failures and any limits on verification.
- [x] Review the diff and existing staged changes. If changes are verified to preserve functionality, commit the dependency changes together with unstaged `plan*.md` files, then push to the configured remote; otherwise report the blocker without pushing.

Audit: `uv lock --check` and pip-audit reported no known vulnerabilities in auditable packages. `crap4py` 0.1.0 is the owner's Git repository pinned at d60a8c0; pip-audit cannot check it, and its GitHub repository reports no published security advisories. npm audit reported zero vulnerabilities. The runtime is Node 22.23.4; CI selects Node 22. Added an engine requirement of >=22.23.4 for the development-only npm tooling.

Verification: `uv run --locked pytest -q` passed 140 tests with 91.91% coverage; `npm run format:check` passed on Node 22.23.4. Only the Node engine declaration and corresponding lockfile metadata changed.
