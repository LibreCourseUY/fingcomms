# Contributing to Fingcomms

Thank you for your interest in contributing to Fingcomms! This guide will walk you through how to contribute, step by step.

## Why Contribute?

Contributing to open source projects allows you to:
- Learn new technologies
- Build a professional portfolio
- Help other students
- Gain experience working in teams

## Code of Conduct

Be respectful to all other contributors. We do not tolerate:
- Discriminatory comments or insults
- Personal or professional harassment
- Publishing private information about others

## How to Contribute

### Step 1: Fork the Repository

A "fork" is a personal copy of the main repository on your GitHub account.

1. Go to: https://github.com/fingdev/fingcomms
2. Click the "Fork" button (top right)
3. Select your GitHub account

### Step 2: Clone Your Fork to Your Computer

```bash
git clone https://github.com/YOUR_USERNAME/fingcomms.git
cd fingcomms
```

### Step 3: Create a New Branch

Never work directly on the `main` branch. Create a new branch for your changes:

```bash
git checkout -b your-branch-name
```

Recommended branch naming:
- `feature/add-search` (for new features)
- `fix/login-error` (for bug fixes)
- `docs/improve-readme` (for documentation)

### Step 4: Make Your Changes

Edit the files you need to modify to add your feature or fix the issue.

### Step 5: Commit Your Changes

A "commit" is like saving a snapshot of your changes.

```bash
git add .
git commit -m "Clear description of what you did"
```

#### Commit Types (Conventional Commits)

We use a standard commit message format:

```
type: brief description
```

**Commit types:**

| Type | When to use |
|------|-------------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation changes |
| `style:` | Code changes that don't affect logic (spacing, formatting) |
| `refactor:` | Rewriting code without changing functionality |
| `test:` | Adding or fixing tests |
| `chore:` | General maintenance tasks |

**Examples:**
```
feat: add category filter to search
fix: correct error when displaying empty groups
docs: add installation instructions
refactor: simplify validation function
```

### Step 6: Push Your Changes to GitHub

```bash
git push origin your-branch-name
```

### Step 7: Create a Pull Request (PR)

A Pull Request is a proposal to add your changes to the original project.

1. Go to your fork on GitHub
2. You'll see a "Compare & pull request" button
3. Click it
4. Fill out the form:
   - **Title**: Briefly describe your changes
   - **Description**: Explain what you did and why
   - **Reviews**: Request review if you know who should review
5. Click "Create Pull Request"

## Issue Templates

Before creating an Issue, check if a similar one already exists.

### Reporting a Bug

Use the Bug template available in the Issues section.

### Suggesting a Feature

Use the Feature template available in the Issues section.

## Code Standards

- We use **English** for code and commit messages
- Follow language conventions (PEP 8 for Python, etc.)
- Add comments when code is not self-explanatory

## How to Test Your Changes

1. Run the application locally:
   ```bash
   docker-compose up --build
   ```

2. Verify your feature works correctly

3. If you add new code, verify it doesn't break anything existing

## Signed Commits (Required)

All commits must be signed. This is a mandatory requirement for contributing.

### Why Signed Commits?

- **Security**: Verifies that you are who you claim to be
- **Integrity**: Guarantees the commit wasn't modified after creation
- **Trust**: Other contributors know changes genuinely come from you
- **Professionalism**: Industry best practice for open source projects

### Setup

Follow our Git Guide to set up your GPG key:
- [GPG Key Setup](https://fingdev.github.io/git)

Configure Git to sign commits by default:
```bash
git config --global commit.gpgsign true
```

## Contributor License Agreement (CLA)

Before contributing, you must read and accept our [Contributor License Agreement (CLA)](https://fingdev.github.io/CLA).

By submitting a Pull Request with cryptographically signed commits, you acknowledge and agree to the CLA terms. This includes:

- Licensing your contribution under MIT
- Confirming you have the rights to contribute the code
- Accepting the project's non-affiliation with FING/Udelar
- Understanding that all commits must be GPG-signed as acceptance of the CLA

Contributions without signed commits or that do not accept the CLA may be rejected.

## Questions?

- If you don't know how to do something, ask in Issues
- If you need help, don't hesitate to ask
- All contributors were where you are now

## Next Steps

Once your PR is approved:
1. A maintainer will merge your changes to the main branch
2. Congratulations! You're now an open source contributor

---

Have a question? Create an Issue and ask!
