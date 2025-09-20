# GitHub Token Security Setup

## Creating a Minimal-Permission Token

1. Go to GitHub Settings > Developer settings > Personal access tokens > Fine-grained tokens
2. Create a new token with **only these permissions**:
   - **Repository access**: Only the specific Hugo site repository
   - **Repository permissions**:
     - Contents: Read and Write (to clone and push)
     - Metadata: Read (required for basic operations)
     - Pull requests: Read (if you want to create PRs from cms-beta)
   
3. **DO NOT GRANT**:
   - Administration permissions
   - Issues permissions  
   - Actions permissions
   - Packages permissions
   - Any other repository permissions

## Additional Security Measures

### Branch Protection Rules (Recommended)
1. In your Hugo site repository settings > Branches
2. Add branch protection rule for `main`:
   - Require pull request reviews before merging
   - Dismiss stale PR approvals when new commits are pushed
   - Require status checks to pass before merging
   - Require branches to be up to date before merging
   - Include administrators (so even you need PR reviews)

### Repository Settings
1. Disable force pushes to `main` branch
2. Enable "Restrict deletions" for `main` branch
3. Consider making the repository private if it isn't already

This way, even if the CMS token is compromised:
- Attacker can only push to `cms-beta` branch
- Cannot delete `main` or `cms-beta` branches
- Cannot bypass PR review requirements
- Cannot access other repositories
