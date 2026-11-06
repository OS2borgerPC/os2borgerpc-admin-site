import json
import urllib.request
from pathlib import Path

import django

from system.models import CoreScriptLibrary, Input, Script, ScriptTag
from system.script_fetcher import fetch_scripts

DEFAULT_CORE_SCRIPT_REPO_URL = "https://github.com/OS2borgerPC/os2borgerpc-core-scripts.git"
DEFAULT_CORE_SCRIPT_REPO = "OS2borgerPC/os2borgerpc-core-scripts"


def _github_get_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "os2borgerpc-admin-site",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _resolve_release_commit_hash(repo_name, tag_name):
    ref_url = f"https://api.github.com/repos/{repo_name}/git/ref/tags/{tag_name}"
    ref_data = _github_get_json(ref_url)
    sha = ref_data.get("object", {}).get("sha")
    if not sha:
        return None
    if ref_data.get("object", {}).get("type") == "tag":
        tag_url = f"https://api.github.com/repos/{repo_name}/git/tags/{sha}"
        tag_data = _github_get_json(tag_url)
        sha = tag_data.get("object", {}).get("sha")
    return sha


def _import_scripts_for_library(repo_url, version_tag, commit_hash, release_date=None):
    scripts = fetch_scripts(repo_url, version_tag, commit_hash)

    library, _ = CoreScriptLibrary.objects.get_or_create(
        commit_hash=commit_hash,
        defaults={
            "repo_url": repo_url,
            "tag": version_tag,
            "release_date": release_date,
            "is_active": False,
        },
    )
    if version_tag and library.tag != version_tag:
        library.tag = version_tag
    if library.repo_url != repo_url:
        library.repo_url = repo_url
    if library.release_date != release_date:
        library.release_date = release_date
    if library.tag != version_tag or library.repo_url != repo_url or library.release_date != release_date:
        library.save(update_fields=["tag", "repo_url", "release_date"])

    for script in scripts:
        versioned_name = f"{script.title} (version: {script.version})"
        script_filters = {"core_script_library": library}
        if script.uid:
            script_filters["uid"] = script.uid
        else:
            script_filters["name"] = versioned_name

        db_script, created = Script.objects.get_or_create(
            defaults={
                "name": versioned_name,
                "description": script.description,
                "site": None,
                "executable_code": None,
                "is_security_script": script.security,
                "is_hidden": script.hidden,
                "maintained_by_magenta": False,
                "feature_permission": None,
                "uid": script.uid,
                "core_script_version": script.version,
                "core_script_library": library,
            },
            **script_filters,
        )

        if not created:
            db_script.name = versioned_name
            db_script.description = script.description
            db_script.is_security_script = script.security
            db_script.is_hidden = script.hidden
            db_script.uid = script.uid
            db_script.core_script_version = script.version
            db_script.core_script_library = library

        source_path = Path(script.sourcePath)
        if source_path.exists():
            with source_path.open("rb") as file:
                db_script.executable_code.save(
                    f"{script.uid or script.title}.sh",
                    django.core.files.File(file),
                    save=False,
                )

        db_script.save()

        tag, _ = ScriptTag.objects.get_or_create(name=script.tag)
        db_script.tags.clear()
        db_script.tags.add(tag)

        position = 0
        db_script.inputs.all().delete()
        for parameter in script.parameters:
            Input.objects.create(
                script=db_script,
                name=parameter.name,
                value_type=parameter.type,
                default_value=parameter.default,
                position=position,
                mandatory=parameter.mandatory,
            )
            position += 1

    return library


def sync_core_script_releases(repo_url=DEFAULT_CORE_SCRIPT_REPO_URL, repo_name=DEFAULT_CORE_SCRIPT_REPO):
    releases_url = f"https://api.github.com/repos/{repo_name}/releases"
    releases = _github_get_json(releases_url)
    created = []

    for release in releases:
        tag_name = release.get("tag_name")
        commit_hash = _resolve_release_commit_hash(repo_name, tag_name) if tag_name else None
        if not tag_name or not commit_hash:
            continue

        release_date = None
        if release.get("published_at"):
            release_date = django.utils.dateparse.parse_datetime(release["published_at"])
        elif release.get("created_at"):
            release_date = django.utils.dateparse.parse_datetime(release["created_at"])
        release_notes = release.get("body") or ""

        library, was_created = CoreScriptLibrary.objects.get_or_create(
            commit_hash=commit_hash,
            defaults={
                "repo_url": repo_url,
                "tag": tag_name,
                "release_date": release_date,
                "release_notes": release_notes,
                "is_active": False,
            },
        )
        if not was_created:
            changed = False
            if library.tag != tag_name:
                library.tag = tag_name
                changed = True
            if library.repo_url != repo_url:
                library.repo_url = repo_url
                changed = True
            if library.release_date != release_date:
                library.release_date = release_date
                changed = True
            if library.release_notes != release_notes:
                library.release_notes = release_notes
                changed = True
            if changed:
                library.save(update_fields=["tag", "repo_url", "release_date", "release_notes"])

        library = _import_scripts_for_library(repo_url, tag_name, commit_hash, release_date)
        if library.release_notes != release_notes:
            library.release_notes = release_notes
            library.save(update_fields=["release_notes"])
        created.append(library)

    return created
