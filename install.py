#!/usr/bin/env python3
"""Install pre-flight into a repository without overwriting existing skills (unless --force is used)."""
import argparse
from pathlib import Path
import shutil

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
    try:
        for destination in destinations:
            if destination.exists() and args.force:
                if destination.is_symlink():
                    destination.unlink()
                else:
                    shutil.rmtree(destination)
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            installed.append(destination)
    except Exception:
        for destination in installed:
            shutil.rmtree(destination)
        raise
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
