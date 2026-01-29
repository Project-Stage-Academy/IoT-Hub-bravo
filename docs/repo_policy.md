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
 