# Repository Policy
 
Branch protection rules and branching strategy for IoT Hub Bravo.
 
## Branch Strategy
 
- **`main`** — production-ready branch. Always stable.
- **Feature branches** — short-lived, created from `main`, merged via PR.
 
See [CONTRIBUTING.md](../CONTRIBUTING.md) for branch naming conventions.
 
## Branch Protection Rules for `main`
 
The following settings should be applied by a repository admin
via **Settings > Branches > Branch protection rules > Add rule** for `main`:
 
### Required Settings
 
| Setting | Value                   | Why                                   |
|---------|-------------------------|---------------------------------------|
| **Require a pull request before merging** | Enabled                 | No direct pushes to main              |
| **Required approvals** | 3                       | At least three reviewers must approve |
| **Dismiss stale PR reviews when new commits are pushed** | Enabled                 | Re-review after changes               |
| **Require status checks to pass before merging** | Enabled                 | CI must pass                          |
| **Required status checks** | `lint`, `test`, `build` | Match CI workflow job names           |
| **Require branches to be up to date before merging** | Enabled                 | Prevent merge conflicts               |
| **Require conversation resolution before merging** | Enabled                 | All review comments addressed         |
| **Do not allow bypassing the above settings** | Enabled                 | Applies to admins too                 |
 
### Recommended Settings
 
| Setting | Value | Why |
|---------|-------|-----|
| **Require signed commits** | Optional | Verify commit authorship |
| **Require linear history** | Optional | Cleaner git log (squash merge) |
| **Restrict who can push to matching branches** | Optional | Limit to maintainers |
| **Allow force pushes** | Disabled | Prevent history rewrite |
| **Allow deletions** | Disabled | Prevent branch deletion |
 
## How to Apply
 
### Via GitHub UI
 
1. Go to **Settings > Branches**
2. Click **Add branch protection rule**
3. Branch name pattern: `main`
4. Enable settings as listed above
5. Click **Create**
 
### Via GitHub CLI
 
```bash
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint", "test", "build"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "restrictions": null
}
EOF
```
 
## Merge Strategy
 
- **Squash merge** is preferred for feature branches (clean history).
- **Merge commit** is acceptable for large branches with meaningful commits.
- **Rebase merge** can be used if the branch has clean, atomic commits.
 
Configure in **Settings > General > Pull Requests**:
- [x] Allow squash merging (default)
- [x] Allow merge commits
- [ ] Allow rebase merging
- [x] Automatically delete head branches
 
## Sample PR Workflow Validation
 
This section documents a validated end-to-end workflow from issue to merge.
 
### Test Run: Django Admin Configuration
 
**Issue:** US-33 — Configure Django Admin for IoT Hub models
 
**1. Branch Creation**
 
```bash
git checkout main
git pull origin main
git checkout -b us-33-django-admin
```
 
Branch name follows convention: `us-<number>-<short-description>`
 
**2. Changes Made**
 
| File | Action |
|------|--------|
| `backend/apps/devices/admin.py` | Register Device, Metric, DeviceMetric, Telemetry models |
| `backend/apps/rules/admin.py` | Register Rule, Event models |
| `backend/apps/users/admin.py` | Register custom User model |
| `backend/apps/devices/models/telemetry.py` | Add formatted_value() helper methods |
| `backend/apps/rules/models/event.py` | Add acknowledged field |
| `backend/apps/users/management/commands/setup_admin.py` | Management command for dev users |
| `backend/tests/test_admin_smoke.py` | Automated smoke tests for admin pages |
| `docs/admin.md` | Admin workflow documentation |
 
**3. Commit Messages**
 
```
feat(admin): register Device and Telemetry models in Django Admin
feat(admin): register Rule and Event models in Django Admin
feat(admin): register custom User model in Django Admin
feat(admin): add bulk enable/disable, CSV export, acknowledge actions
feat(models): add formatted_value methods to Telemetry model
feat(models): add acknowledged field to Event model
chore(admin): add setup_admin management command
test(admin): add smoke tests for admin pages
docs(admin): add admin workflow and role documentation
```
 
**4. Push and PR**
 
```bash
git push -u origin us-33-django-admin
gh pr create --title "PR US33 Configure Django Admin" --body "..."
```
 
**5. CI Verification**
 
- [x] `lint` job passes (black, ruff)
- [x] `test` job passes (pytest with 22 admin smoke tests)
- [x] `build` job passes (Docker image)
 
**6. Review and Merge**
 
- [x] PR created with description and linked issue
- [x] At least 1 reviewer approved
- [x] Review feedback addressed (permission checks, format_html fixes)
- [x] All CI checks passed
- [x] Squash merged into `main`
- [x] Branch deleted after merge
 
### Result
 
Workflow validated successfully. All steps from CONTRIBUTING.md were followed.
 