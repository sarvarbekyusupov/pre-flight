#!/usr/bin/env python3
"""Install pre-flight into a repository without overwriting existing skills (unless --force is used)."""
import argparse
from pathlib import Path
import shutil
import tempfile
import time

TARGETS = {'claude': '.claude/skills', 'codex': '.agents/skills', 'gemini': '.gemini/skills'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--agent', choices=[*TARGETS, 'all'], default='all')
    parser.add_argument('--init-rules', action='store_true', help='Initialize .pre-flight/rules.md from template if not present')
    parser.add_argument('--force', action='store_true', help='Overwrite existing pre-flight installations')
    args = parser.parse_args()
    root = args.repo.expanduser().resolve()
    if not root.is_dir():
        parser.error('Target repository directory must exist.')
    source = Path(__file__).resolve().parent / 'pre-flight'
    selected = TARGETS if args.agent == 'all' else {args.agent: TARGETS[args.agent]}
    destinations = [root / path / 'pre-flight' for path in selected.values()]
    
    for destination in destinations:
        if destination.exists() or destination.is_symlink():
            if not args.force:
                parser.error(f'Refusing to overwrite {destination}; use --force to update or inspect/remove the old copy explicitly.')
        if not destination.resolve().is_relative_to(root):
            parser.error('Refusing destination outside repository through symlinks.')
            
    installed = []
    backups = []
    timestamp = int(time.time())
    
    # Use a staging directory on the same filesystem to prevent cross-device (EXDEV) errors
    staging_root = root / '.pre-flight' / 'staging'
    staging_root.mkdir(parents=True, exist_ok=True)
    
    try:
        with tempfile.TemporaryDirectory(dir=staging_root) as staging_dir:
            staging_path = Path(staging_dir)
            staged_dests = []
            
            # Phase 1: Stage all copies in isolation. Failures here do not touch the active installation.
            for i, destination in enumerate(destinations):
                staged = staging_path / f"staged_{i}"
                shutil.copytree(source, staged, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                staged_dests.append((destination, staged))
            
            # Phase 2: Atomically swap the staged copies into place.
            try:
                for destination, staged in staged_dests:
                    backup = None
                    if destination.exists() or destination.is_symlink():
                        if args.force:
                            backup = destination.with_name(f"{destination.name}.bak.{timestamp}")
                            # rename works on symlinks too (backs up the link itself)
                            destination.rename(backup)
                            backups.append((destination, backup))
                    
                    # Ensure parent directories exist before moving
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    staged.rename(destination)
                    installed.append(destination)
            except Exception:
                # Rollback Phase 2: restore backups and remove partial installations
                for destination in installed:
                    if destination.exists() or destination.is_symlink():
                        if destination.is_symlink():
                            destination.unlink()
                        else:
                            shutil.rmtree(destination)
                for original, backup in backups:
                    if backup.exists() or backup.is_symlink():
                        backup.rename(original)
                raise
    except Exception:
        raise
    finally:
        # Clean up the staging root if it's empty
        if staging_root.exists() and not any(staging_root.iterdir()):
            staging_root.rmdir()
    
    # Cleanup successful backups
    for original, backup in backups:
        if backup.exists() or backup.is_symlink():
            if backup.is_symlink():
                backup.unlink()
            else:
                shutil.rmtree(backup)

    for destination in installed:
        print(f'Installed: {destination}')

    if args.init_rules:
        rules_dir = root / '.pre-flight'
        rules_file = rules_dir / 'rules.md'
        template_file = source / 'references' / 'rules.template.md'
        if not rules_file.exists() and template_file.exists():
            rules_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(template_file, rules_file)
            print(f'Initialized rules: {rules_file}')
        elif rules_file.exists():
            print(f'Existing rules file preserved: {rules_file}')


if __name__ == '__main__':
    main()
