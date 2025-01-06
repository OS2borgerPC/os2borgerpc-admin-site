import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import yaml
from dataclasses import dataclass, field
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

def fetch_scripts(repoUrl, versionTag, commitHash):
    repo_url = repoUrl
    clone_path = Path("downloaded_core_scripts") / get_repo_name(repo_url) / commitHash

    # Perform a shallow clone if the repository isn't already cloned
    if not (clone_path).exists():
        if versionTag:
            # Check that the commitHash matches the versionTag
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", versionTag, repo_url, str(clone_path)], 
                check=True
            )

            versionTagCommitHash = subprocess.run(
                ["git", "-C", str(clone_path), "rev-parse", versionTag], 
                check=True, 
                capture_output=True,
                text=True
            ).stdout.strip()

            if versionTagCommitHash != commitHash:
                logger.warning(f"The commit hash for tag '{versionTag}' is '{versionTagCommitHash}', which does not match the provided commit hash '{commitHash}'.")
                return []
        else:
            # Clone the repository and then check out the specific commit hash
            subprocess.run(
                ["git", "clone", "--filter=blob:none", repo_url, str(clone_path)], 
                check=True
            )
            subprocess.run(
                ["git", "-C", str(clone_path), "checkout", commitHash],
                check=True
            )

    # Retrieve content of all markdown (.md) files, and convert them to Scripts
    scripts = []
    md_dir_path = clone_path
    for md_file in md_dir_path.glob("**/*.md"):
        if md_file.is_file():
            if md_file.name == "README.md":
                continue
            with open(md_file, 'r') as file:
                file_content = file.read()
                try:
                    script = parse_md_to_script(file_content, clone_path)
                except Exception as e:
                    logger.warning("Skipping script file '" + str(md_file.relative_to(md_dir_path)) + "' because it's content is not formatted correctly:")
                    logger.warning(file_content)
                    logger.warning(f"Exception: {e}")
                    continue
                if not Path(script.sourcePath).exists() and not Path(script.sourcePath).is_file():
                    logger.warning("Skipping " + str(md_file.relative_to(md_dir_path)) + " because the 'source' attribute does not point to a valid file.")
                    continue
                scripts.append(script)

    return scripts


@dataclass
class Parameter:
    name: str
    type: str
    default: Optional[str]
    mandatory: bool

@dataclass
class Script:
    title: str
    version: str
    parent: str
    sourcePath: str
    compatible_versions: Optional[str]
    compatible_images: List[str]
    description: str
    tag: str
    partners: Optional[str]
    hidden: Optional[bool]
    security: Optional[bool]
    uid: Optional[str]
    parameters: List[Parameter] = field(default_factory=list)

def parse_md_to_script(content: str, clone_path: Path) -> Script:
    # Split YAML and Markdown content
    yamlBegin, yaml_string, markdown_string = content.split("---", 2)
    yaml_string = yaml_string.strip()
    markdown_string = markdown_string.strip()

    # Parse the YAML content
    yaml_content = yaml.safe_load(yaml_string)

    # Parse parameters
    params = yaml_content.get('parameters', [])
    params = params if params is not None else []

    # Extract parameters to list
    parameters = [
        Parameter(
            name=param['name'],
            type=param['type'].upper(),
            default=param['default'],
            mandatory=param['mandatory']
        )
        for param in params
    ]

    return Script(
        title=yaml_content.get('title'),
        version=yaml_content.get('version'),
        parent=yaml_content.get('parent'),
        sourcePath=str(clone_path / yaml_content.get('source')),
        compatible_versions=yaml_content.get('compatible_versions'),
        compatible_images=yaml_content.get('compatible_images', []),
        description=markdown_string,
        tag=yaml_content.get('parent'),
        partners=yaml_content.get('partners'),
        parameters=parameters,
        hidden=yaml_content.get('hidden', False),
        security=yaml_content.get('security', False),
        uid=yaml_content.get('uid', None),
    )

def get_repo_name(repo_url):
    # Parse the URL
    parsed_url = urlparse(repo_url)
    
    # Extract the path from the URL and split to get the repository name
    repo_name = os.path.basename(parsed_url.path)

    # Remove the ".git" extension if present
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    return repo_name