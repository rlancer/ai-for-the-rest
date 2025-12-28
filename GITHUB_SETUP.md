# GitHub Setup Instructions

This document describes how to configure GitHub secrets and branch protection for the repository.

## Prerequisites

1. Install GitHub CLI: `scoop install gh`
2. Authenticate: `gh auth login`
3. Ensure you have admin access to the repository

## Automated Setup

Run the setup script with Bun:

```bash
bun run scripts/setup-github.ts
```

The script will prompt you for your PyPI token. You can skip it and add it later using:

```bash
gh secret set PYPI_TOKEN
# Paste your token when prompted
```

## Manual Setup

If you prefer to run commands manually:

### 1. Store PyPI Token

First, create a PyPI API token at https://pypi.org/manage/account/token/

Then store it as a GitHub secret:

```bash
# Set PYPI_TOKEN secret
gh secret set PYPI_TOKEN

# You'll be prompted to paste your token
```

### 2. Enable Branch Protection

Protect the main branch to require PRs with approval:

```bash
# Get your repository name (e.g., rlancer/ai-for-the-rest)
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

# Enable branch protection with PR requirements
gh api -X PUT "repos/$REPO/branches/main/protection" \
  -f required_status_checks='{"strict":true,"contexts":["test"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"dismissal_restrictions":{},"dismiss_stale_reviews":true,"require_code_owner_reviews":false,"required_approving_review_count":1,"require_last_push_approval":false,"bypass_pull_request_allowances":{}}' \
  -f restrictions=null \
  -f required_linear_history=false \
  -f allow_force_pushes=false \
  -f allow_deletions=false

# Verify protection is enabled
gh api "repos/$REPO/branches/main/protection"
```

### 3. Branch Protection Rules Summary

The configuration above sets:
- **Require pull request reviews**: 1 approval required
- **Dismiss stale reviews**: When new commits are pushed
- **Require status checks**: CI tests must pass
- **No force pushes**: Prevents rewriting history
- **No deletions**: Prevents branch deletion
- **Enforce for admins**: Rules apply to everyone

## GitHub Actions Workflows

Two workflows have been created:

### CI Workflow (`.github/workflows/ci.yml`)
- Runs on every push to main and on all PRs
- Tests on Windows, macOS, and Linux
- Tests with Python 3.11 and 3.12
- Runs linting with ruff
- The `test` job is required to pass before merging

### Publish Workflow (`.github/workflows/publish.yml`)
- Runs when you create a version tag (e.g., `v0.1.0`)
- Runs tests before publishing
- Publishes to PyPI using the stored token
- Creates a GitHub release with artifacts

## Publishing a Release

To publish a new version:

```bash
# 1. Update version in packages/cli/pyproject.toml
# 2. Commit the version bump
git add packages/cli/pyproject.toml
git commit -m "Bump version to 0.1.0"
git push

# 3. Create and push a tag
git tag v0.1.0
git push origin v0.1.0

# 4. The publish workflow will automatically run
```

## Troubleshooting

### "Resource not accessible by integration"
You need admin permissions on the repository to set branch protection rules.

### "Required status check is not available"
The status check names must match the job names in your CI workflow. The `test` job will become available after the first CI run.

### PyPI publishing fails
Ensure your PyPI token has the correct permissions and is stored as `PYPI_TOKEN` secret.

## Verifying Setup

Check if everything is configured:

```bash
# Check secrets
gh secret list

# Check branch protection
gh api repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/branches/main/protection

# List workflows
gh workflow list

# View recent workflow runs
gh run list --limit 5
```
