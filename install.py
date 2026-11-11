#!/usr/bin/env python3
"""Install pre-flight into a repository without overwriting existing skills."""
import argparse
from pathlib import Path
import shutil

TARGETS = {'claude': '.claude/skills', 'codex': '.agents/skills', 'gemini': '.gemini/skills'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--agent', choices=[*TARGETS, 'all'], default='all')
    args = parser.parse_args()
    root = args.repo.expanduser().resolve()
    if not root.is_dir():
        parser.error('Target repository directory must exist.')
    source = Path(__file__).resolve().parent / 'pre-flight'
    selected = TARGETS if args.agent == 'all' else {args.agent: TARGETS[args.agent]}
    destinations = [root / path / 'pre-flight' for path in selected.values()]
    for destination in destinations:
        if destination.exists() or destination.is_symlink():
            parser.error(f'Refusing to overwrite {destination}; inspect/remove the old copy explicitly.')
        if not destination.resolve().is_relative_to(root):
            parser.error('Refusing destination outside repository through symlinks.')
    installed = []
    try:
        for destination in destinations:
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            installed.append(destination)
    except Exception:
        for destination in installed:
            shutil.rmtree(destination)
        raise
    for destination in installed:
        print(f'Installed: {destination}')


if __name__ == '__main__':
    main()
