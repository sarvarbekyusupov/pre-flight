#!/usr/bin/env python3
"""Install pre-flight into a project; --force replaces an existing skill safely."""
import argparse
from pathlib import Path
import shutil
import tempfile

TARGETS = {'claude': '.claude/skills', 'codex': '.agents/skills', 'gemini': '.gemini/skills'}


def present(path):
    return path.exists() or path.is_symlink()


def install(source, root, agents, force=False, init_rules=False):
    root = root.resolve()
    source = source.resolve()
    if not (source / 'SKILL.md').is_file():
        raise ValueError('Skill source is missing SKILL.md.')
    destinations = [root / TARGETS[a] / 'pre-flight' for a in agents]
    for dest in destinations:
        if not dest.resolve().is_relative_to(root):
            raise ValueError(f'Destination escapes project: {dest}')
        if present(dest) and not force:
            raise ValueError(f'Already installed: {dest}; use --force to update.')
        if present(dest) and not dest.is_symlink() and not dest.is_dir():
            raise ValueError(f'Refusing non-directory destination: {dest}')
        if dest.resolve() == source:
            raise ValueError('Cannot replace the skill source with itself.')
    rules = root / '.pre-flight' / 'rules.md'
    if init_rules and not rules.resolve().is_relative_to(root):
        raise ValueError('Rules destination escapes project.')
    # Each staging directory lives beside its destination, including mount points.
    transactions = []
    rules_created = False
    try:
        for dest in destinations:
            dest.parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix='.pre-flight-install-', dir=dest.parent))
            entry = {'dest': dest, 'stage': stage, 'backup': stage / 'previous', 'installed': False}
            transactions.append(entry)
            shutil.copytree(source, stage / 'new', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for entry in transactions:
            dest = entry['dest']
            if present(dest):
                if not force:
                    raise ValueError(f'Destination appeared during installation: {dest}')
                dest.rename(entry['backup'])
            (entry['stage'] / 'new').rename(dest)
            entry['installed'] = True
        if init_rules and not present(rules):
            rules.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive creation preserves rules created by another process.
            template = (source / 'references' / 'rules.template.md').read_text()
            try:
                with rules.open('x') as handle:
                    rules_created = True
                    handle.write(template)
            except FileExistsError:
                pass
    except BaseException as original_error:
        recovery_errors = []
        if rules_created:
            try:
                rules.unlink()
            except OSError as exc:
                recovery_errors.append(str(exc))
        for entry in reversed(transactions):
            try:
                if entry['installed']:
                    shutil.rmtree(entry['dest'])
                if present(entry['backup']):
                    entry['backup'].rename(entry['dest'])
            except OSError as exc:
                recovery_errors.append(f"{exc}; recovery files: {entry['stage']}")
        if recovery_errors:
            # Never delete a backup when restoration failed.
            raise RuntimeError('Recovery incomplete: ' + '; '.join(recovery_errors)) from original_error
        for entry in transactions:
            shutil.rmtree(entry['stage'])
        raise
    for entry in transactions:
        try:
            shutil.rmtree(entry['stage'])
        except OSError as exc:
            print(f"Warning: installation succeeded; backup cleanup needed at {entry['stage']}: {exc}")
    return destinations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--agent', choices=[*TARGETS, 'all'], default='all')
    parser.add_argument('--init-rules', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    root = args.repo.expanduser().resolve()
    if not root.is_dir():
        parser.error('Target repository directory must exist.')
    agents = list(TARGETS) if args.agent == 'all' else [args.agent]
    try:
        destinations = install(Path(__file__).resolve().parent / 'pre-flight', root, agents,
                               args.force, args.init_rules)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f'Installation failed: {exc}\n')
    for dest in destinations:
        print(f'Installed: {dest}')


if __name__ == '__main__':
    main()
