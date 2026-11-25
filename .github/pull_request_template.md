## What does this change?

<!-- One or two sentences. Link the requirement or use case (e.g. FR-11, UC-06). -->

## Review checklist (quality gate G2)

- [ ] CI is green (lint, McCabe <= 10, Bandit, audits, tests, coverage, dogfooding, E2E)
- [ ] New or changed behaviour has tests; test names say which requirement they verify
- [ ] No analysed code is executed; external tools are called with argument lists, never a shell
- [ ] User input is validated; errors tell the user what to fix (NFR-14)
- [ ] No secrets, tokens or personal data in code, logs or fixtures
- [ ] UI changes checked with keyboard and pass the accessibility test
- [ ] Docs updated (README, decisions, code review log) if behaviour or design changed

## AI usage (DIR)

<!-- Did you use AI for this change? Which tool, for what, and how did you verify the result?
     Add a row to the DIR declaration. -->
