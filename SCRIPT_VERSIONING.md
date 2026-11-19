# Core Script Versioning and Migration Guide

## Overview

This document explains how core scripts are versioned, stored, and displayed in the OS2borgerPC admin system.

## Problem Statement

Previously, the system used both a commit hash and version tag to identify core script releases. This caused:
- Confusion about which identifier was actually being used
- Potential for duplicate scripts when updating releases
- No clear way to track which release a script came from

## Solution

The system now uses a **single commit hash** to identify and track all core scripts. This commit hash is:
- Stored in the database with every script
- Used to filter which scripts are displayed to users
- Used to prevent duplicate scripts on re-runs

## How It Works

### Script Storage

Each script record in the database has a `core_script_commit_hash` field that contains the git commit hash from the release it was fetched from.

**Example:**
```
Script: "Installer Chrome (version: 1)"
  - commit_hash: db319672efdcc0f7402c4a7370aa763be9960c38
  - is_hidden: False

Script: "Installer Chrome (version: 1)" 
  - commit_hash: abc123def456... (different release)
  - is_hidden: False
```

### Display Filtering

Users only see scripts whose `commit_hash` matches the `CORE_SCRIPT_COMMIT_HASH` environment variable set in `docker-compose.yaml`.

**Benefits:**
- ✅ Old script versions remain in the database (preserved history)
- ✅ No duplicates appear in the user interface
- ✅ All scripts can still be accessed via direct links (job history)
- ✅ Admins can view all versions in `/admin/system/script/`

### Admin Panel

The admin panel displays all scripts across all releases with their commit hashes visible, making it easy to identify which scripts belong to which release.

## Updating to a New Core Script Release

### Prerequisites

You need:
1. The old release's commit hash (e.g., `db319672efdcc0f7402c4a7370aa763be9960c38`)
2. The new release's commit hash

### Step-by-Step Process

#### Step 1: Migrate Legacy Scripts (First Time Only)

If you have scripts with NULL commit hash (from before this feature was implemented), assign them to the legacy hash:

```bash
docker compose exec -T os2borgerpc-admin python manage.py migrate_legacy_scripts \
  --legacyHash db319672efdcc0f7402c4a7370aa763be9960c38
```

This command:
- Finds all scripts with no commit hash
- Assigns them the legacy hash you provide
- Preserves their history and links in job logs

**Output example:**
```
Successfully migrated 75 scripts to legacy hash: db319672efdcc0f7402c4a7370aa763be9960c38
```

#### Step 2: Update Docker Compose

Edit `compose.yaml` and change the `CORE_SCRIPT_COMMIT_HASH` environment variable:

```yaml
environment:
  CORE_SCRIPT_COMMIT_HASH: <new-commit-hash>
```

#### Step 3: Pull New Scripts

Restart the containers:

```bash
docker compose up -d
```

This automatically:
- Fetches the new scripts from the specified commit
- Stores them with the new commit hash
- Prevents duplicates if run multiple times with the same hash

### Result

After these steps:
- ✅ Users see only scripts from the new release
- ✅ Old scripts remain in database with legacy hash
- ✅ Users can still access old scripts from job history
- ✅ No duplicate scripts appear in the interface

## Example Scenario

**Initial state:** Server running commit `db31967...` with 75 scripts

**Step 1:** Migrate legacy scripts
```bash
docker compose exec -T os2borgerpc-admin python manage.py migrate_legacy_scripts \
  --legacyHash db319672efdcc0f7402c4a7370aa763be9960c38
```
- Assigns legacy hash to any NULL-hash scripts

**Step 2:** Update compose.yaml
```yaml
CORE_SCRIPT_COMMIT_HASH: a1b2c3d4e5f6a7b8...  # new release
```

**Step 3:** Restart
```bash
docker compose up -d
```

**Final state:** Database has 150 scripts total:
- 75 scripts with hash `db31967...` (old release, hidden from users)
- 75 scripts with hash `a1b2c3...` (new release, visible to users)

## Accessing Old Scripts

Old scripts are not deleted and remain accessible via:

1. **Direct links** - Job history contains links to old scripts, which still work
2. **Admin panel** - View all versions at `/admin/system/script/`
3. **Database** - Full history is preserved for auditing

## Technical Details

### Duplicate Prevention

The fetch command checks before creating each script:

```python
# Only create if this exact name+hash combo doesn't exist
if not Script.objects.filter(
    name=script_name, 
    core_script_commit_hash=commit_hash
).exists():
    # Create new script
```

This prevents duplicates even if `docker compose up` is run multiple times with the same hash.

### View Filtering

When displaying scripts to users, all queries include:

```python
Script.objects.filter(
    core_script_commit_hash=settings.CORE_SCRIPT_COMMIT_HASH,
    is_hidden=False,  # Other filters...
)
```

This ensures users only see the current release.

## Troubleshooting

### I see duplicate scripts in the user interface

**Cause:** Mismatch between database hashes and `CORE_SCRIPT_COMMIT_HASH` environment variable

**Fix:** 
1. Check `docker compose.yaml` for the correct hash
2. Verify scripts in database have the right hashes via admin panel
3. Restart containers: `docker compose restart`

### Old scripts aren't showing in job history

**Cause:** Jobs linked to scripts that were deleted

**Fix:** Use the migration command before updating:
```bash
docker compose exec -T os2borgerpc-admin python manage.py migrate_legacy_scripts \
  --legacyHash <old-hash>
```

### I need to rollback to a previous release

Simply change the `CORE_SCRIPT_COMMIT_HASH` back to the old value and restart. Users will immediately see the old scripts again (they were never deleted).

## Related Commands

```bash
# Fetch and install scripts for a specific commit
docker compose exec -T os2borgerpc-admin python manage.py \
  fetch_and_install_core_scripts --commitHash <hash>

# Migrate NULL-hash scripts to a legacy hash
docker compose exec -T os2borgerpc-admin python manage.py \
  migrate_legacy_scripts --legacyHash <hash>

# Check script hashes in database
docker compose exec -T os2borgerpc-admin python manage.py shell <<'EOF'
from system.models import Script
from django.db.models import Count

for entry in Script.objects.values('core_script_commit_hash').annotate(count=Count('id')):
    hash_val = entry['core_script_commit_hash'] or 'None'
    print(f"{hash_val}: {entry['count']} scripts")
EOF
```
