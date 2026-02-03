# Team Roles and Responsibilities

## Owner
- Overall project oversight and decision-making
- Final approval on major changes

## Backend Lead
- Backend architecture and development
- API design and implementation
- Database management

## DevOps Lead
- Infrastructure setup and maintenance
- CI/CD pipeline configuration
- Deployment and monitoring

## QA
- Testing and quality assurance
- Bug reporting and verification
- Test case development

## Docs
- Documentation maintenance
- API documentation
- User guides and README updates

# Contributing to IoT Hub Bravo
 
Thank you for your interest in contributing! This guide covers the workflow,
conventions, and expectations for all contributors.
 
## Table of Contents
 
- [Getting Started](#getting-started)
- [Team Roles](#team-roles)
- [Branching Strategy](#branching-strategy)
- [Commit Message Conventions](#commit-message-conventions)
- [Pull Request Workflow](#pull-request-workflow)
- [PR Checklist](#pr-checklist)
- [Code Style](#code-style)
- [Running Tests](#running-tests)
 
---
 
## Getting Started
 
1. Clone the repository:
   ```bash
   git clone https://github.com/Project-Stage-Academy/IoT-Hub-bravo.git
   cd IoT-Hub-bravo
   ```
2. Copy `.env.example` to `.env` and configure values.
3. Start the development stack:
   ```bash
   docker compose up -d --build
   ```
4. Run migrations:
   ```bash
   docker compose exec backend python manage.py migrate
   ```
5. Create dev users (optional):
   ```bash
   docker compose exec backend python manage.py setup_admin
   ```
 
## Branching Strategy
 
- **`main`** — stable, protected branch. All merges via PR only.
- **Feature branches** — created from `main`, named by convention:
 
| Branch type | Pattern | Example |
|-------------|---------|---------|
| User story | `us-<number>-<short-description>` | `us-42-device-admin` |
| Feature | `ftr-<number>-<short-description>` | `ftr-15-csv-export` |
| Bug fix | `bug-<number>-<short-description>` | `bug-7-login-redirect` |
| Hotfix | `hotfix-<short-description>` | `hotfix-ci-build` |
 
### Rules
 
- Always branch from latest `main`.
- Keep branches short-lived — merge within a few days.
- Delete branch after merge.
 
## Commit Message Conventions
 
We follow [Conventional Commits](https://www.conventionalcommits.org/):
 
```
<type>(<scope>): <short description>
 
[optional body]
 
[optional footer]
```
 
### Types
 
| Type | Usage |
|------|-------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Build process, dependencies, tooling |
| `ci` | CI/CD configuration changes |
 
### Examples
 
```
feat(devices): add bulk enable/disable admin action
fix(rules): correct metric_type field reference in search
docs(admin): add admin workflow documentation
test(admin): add smoke tests for admin pages
chore(deps): update Django to 5.2.10
```
 
## Pull Request Workflow
 
1. Create a branch from `main` following the naming convention.
2. Make your changes with clear, conventional commits.
3. Push your branch and open a PR.
4. Fill in the PR template completely.
5. Ensure CI passes (lint + tests + build).
6. Request review from at least one team member.
7. Address review feedback.
8. Merge after approval (squash merge preferred).
9. Delete the branch after merge.
 
### PR Title Format
 
```
PR US/FTR/BUG[<number>] <short description>
```
 
Example: `PR US42 Add device admin configuration`
 
## PR Checklist
 
Before requesting review, verify:
 
- [ ] Branch is up to date with `main`
- [ ] All new code has tests
- [ ] All tests pass (`pytest`)
- [ ] Linting passes (`black`, `ruff`)
- [ ] Documentation updated (if applicable)
- [ ] PR links to the related issue/story
- [ ] PR description explains **what** and **why**
- [ ] No secrets or credentials in the code
- [ ] Migration files included (if models changed)
 
## Code Style
 
- **Formatter:** [Black](https://black.readthedocs.io/) (default config)
- **Linter:** [Ruff](https://docs.astral.sh/ruff/)
- **Language:** All code, comments, and documentation in English
 
Run locally before pushing:
 
```bash
black backend/
ruff check backend/
```
 
## Running Tests
 
```bash
# All tests
docker compose exec backend pytest
 
# Specific test file
docker compose exec backend pytest tests/test_admin_smoke.py -v
 
# With coverage
docker compose exec backend pytest --cov=apps --cov-report=term-missing
```
 
---
 
For API conventions, see [docs/api-guide.md](docs/api-guide.md).
