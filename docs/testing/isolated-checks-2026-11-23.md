# PR 1 — validation and SQLite isolation

Baseline: origin/dev b929ea268c1440b52633711a1db66f75600e583b. Branch: codex/ff-sb-01-isolated-checks.
SQLite was confirmed on 23 November 2026. Work used a clean clone and fresh Python 3.13 venv in /private/tmp; the main workspace was preserved.

## RED before implementation

- New frontend checks-isolation.cjs: all 16 combinations of four commands, two env names and root/frontend locations failed the refusal assertion. Stub tools executed despite fake env files.
- New test_test_environment_isolation.py: the subprocess loaded the fake dotenv sentinel during collection; the default project path was backend/.data rather than pytest's tmp_path. No DB was opened at that default path.
- pnpm lint with dependency auto-install disabled exited 1 and displayed the interactive ESLint setup prompt.
- An earlier frontend attempt hit pnpm 11's automatic dependency installation/network timeout. That is not counted as a RED behavior result. Dependencies were restored with npm ci before the valid RED runs above.

## Change

- The four check scripts refuse env files in the repository root or frontend before invoking tools. .env.example is allowed. Normal dev/start scripts are unchanged; clean-checkout builds pass required QA values explicitly.
- pnpm only runs scripts: verifyDepsBeforeRun is false, dependencies remain installed from package-lock.json with npm ci. No lockfile change.
- Pytest sets PYTHON_DOTENV_DISABLED before application test collection; its default project and derived image stores use tmp_path alongside the existing isolated dataset fixture.
- Added Next core-web-vitals lint configuration. Lint exposed three pre-existing home-page anchor errors; these now use next/link with the same href/text.
- CI installs pnpm 11.13.1, executes the exact required frontend chain and disables backend dotenv. No existing test expectations were edited.

## GREEN

- Same new frontend assertions: passed, including env-file refusal and successful execution with only .env.example.
- Same backend subprocess probe: passed; SQLite was actually created under pytest's temporary directory.
- Frontend: pnpm typecheck && pnpm lint && pnpm test && pnpm build && git diff --check passed; 26 suites.
- Backend: PYTHON_DOTENV_DISABLED=1 python -m pytest -q passed: 865 passed, 1 skipped.
- No env files or backend/.data files were present in the validation clone. No model calls or production services were used.

Lint/build still report existing React-hook/image warnings and next lint deprecation; backend reports an existing Starlette/httpx warning. These were not suppressed. This is verification of test isolation and gates, not creative-quality, browser or deployment acceptance. GitHub CI status must be checked separately on the PR head.

Raw local logs are retained at artifacts/sb-pr1-20261123 in the main workspace, outside the PR diff.
