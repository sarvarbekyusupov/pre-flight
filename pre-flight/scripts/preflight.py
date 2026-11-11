#!/usr/bin/env python3
"""Pre-flight metadata collector and explicit check runner. Python 3.9+, Git."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time


def git(repo, *args, optional=False):
    result = subprocess.run(['git', '-C', str(repo), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=30)
    if result.returncode and not optional:
        raise ValueError(result.stderr.decode(errors='replace').strip())
    return result.stdout if result.returncode == 0 else None


def paths(repo, *args):
    return [os.fsdecode(p) for p in git(repo, *args).split(b'\0') if p]


def collect(repo, scope='all', base=None, rules_filters=None, commit_policy='off'):
    if commit_policy not in ('off', 'conventional', 'ticket-or-conventional'):
        raise ValueError('Unknown commit policy.')
    root = Path(os.fsdecode(git(repo, 'rev-parse', '--show-toplevel')).strip())
    head = git(root, 'rev-parse', '--verify', 'HEAD', optional=True)
    if head is None:
        raise ValueError('Repository has no HEAD commit; create an initial commit before review.')
    branch_raw = git(root, 'rev-parse', '--abbrev-ref', 'HEAD', optional=True)
    branch = branch_raw.decode().strip() if branch_raw else None
    result = {'commit_policy': commit_policy, 'repository': str(root), 'branch': branch, 'scope': scope, 'head': head.decode().strip(),
              'base': None, 'merge_base': None, 'layers': {}, 'warnings': [],
              'conflicts': paths(root, 'diff', '--name-only', '--diff-filter=U', '-z')}
    if scope in ('all', 'branch'):
        candidates = [base] if base else [
            'origin/HEAD', 'origin/main', 'origin/dev', 'origin/develop',
            'origin/master', 'main', 'dev', 'develop', 'master'
        ]
        for candidate in candidates:
            sha = git(root, 'rev-parse', '--verify', '--end-of-options', candidate + '^{commit}', optional=True)
            if sha:
                sha = sha.decode().strip()
                merge = git(root, 'merge-base', sha, 'HEAD', optional=True)
                if merge:
                    result.update(base=candidate, merge_base=merge.decode().strip())
                    break
        if not result['merge_base']:
            raise ValueError('No usable base/merge-base. Pass --base REF; remote refs are not fetched automatically.')
        result['warnings'].append('Base uses local refs, which may be stale; no network fetch performed.')
        result['layers']['branch'] = paths(root, 'diff', '--no-ext-diff', '--no-textconv', '--name-only', '-z', result['merge_base'], 'HEAD', '--')

        commits_raw = git(root, 'log', '--no-merges', '--format=%H%x1f%s%x1f%an', f"{result['merge_base']}..HEAD", optional=True)
        commits = []
        if commits_raw:
            for line in commits_raw.decode(errors='replace').splitlines():
                if line.strip():
                    parts = line.split('\x1f')
                    if len(parts) == 3:
                        commits.append({'sha': parts[0], 'subject': parts[1], 'author': parts[2]})
        result['commits'] = commits

        wip_pattern = re.compile(r'^(wip\b|fixup!|squash!|backup\b|tmp\b|temp\b|review fixes\b)', re.IGNORECASE)
        cc_pattern = re.compile(r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([^)]+\))?(!)?:\s')
        ticket_match = re.match(r'^(?:feature|bugfix|hotfix)/([A-Z]{2,}-[0-9]+)', branch or '')
        ticket_key = ticket_match.group(1) if ticket_match else None

        hygiene_warnings = []
        for c in commits:
            subj = c['subject']
            if wip_pattern.search(subj):
                hygiene_warnings.append(f"Commit {c['sha'][:8]} has work-in-progress subject: '{subj}'")
                continue
            
            # Branch names supply ticket context only; they never enable enforcement.
            if commit_policy != 'off':
                has_ticket = (commit_policy == 'ticket-or-conventional' and ticket_key and
                              (subj.startswith(f"{ticket_key}. ") or subj.startswith(f"{ticket_key}: ")))
                has_cc = bool(cc_pattern.match(subj))
                
                if not has_ticket and not has_cc:
                    hygiene_warnings.append(f"Commit {c['sha'][:8]} violates explicit {commit_policy} policy: '{subj}'")

        if hygiene_warnings:
            result['commit_hygiene_warnings'] = hygiene_warnings

    if scope in ('all', 'staged'):
        result['layers']['staged'] = paths(root, 'diff', '--no-ext-diff', '--no-textconv', '--cached', '--name-only', '-z', '--')
    if scope in ('all', 'working'):
        result['layers']['unstaged'] = paths(root, 'diff', '--no-ext-diff', '--no-textconv', '--name-only', '-z', '--')
        if scope == 'working':
            result['layers']['since_head'] = paths(root, 'diff', '--no-ext-diff', '--no-textconv', '--name-only', '-z', 'HEAD', '--')
        result['layers']['untracked'] = paths(root, 'ls-files', '--others', '--exclude-standard', '-z')
    result['files'] = sorted(set(p for layer in result['layers'].values() for p in layer))

    def extract_module(path_str):
        parts = Path(path_str).parts
        if len(parts) >= 2 and parts[0] in ('apps', 'libs', 'packages', 'services', 'modules'):
            return f"{parts[0]}/{parts[1]}"
        elif len(parts) > 1:
            return parts[0]
        return ''

    affected_modules = sorted(set(extract_module(f) for f in result['files'] if extract_module(f)))
    if affected_modules:
        result['affected_modules'] = affected_modules

    if rules_filters:
        rules_path = root / '.pre-flight' / 'rules.md'
        if rules_path.exists():
            content = rules_path.read_text()
            filtered_sections = []
            current_section = []
            include = False
            for line in content.splitlines():
                if line.startswith('## '):
                    if current_section and include:
                        filtered_sections.append('\n'.join(current_section))
                    current_section = [line]
                    header = line[3:].strip().lower()
                    include = any(f.lower() in header for f in rules_filters)
                elif current_section:
                    current_section.append(line)
            if current_section and include:
                filtered_sections.append('\n'.join(current_section))
            
            if filtered_sections:
                result['active_rules'] = '\n\n'.join(filtered_sections)
            else:
                result['warnings'].append(f'No sections in rules.md matched filters: {rules_filters}')

    result['execution_scope'] = 'Checks execute against current working tree, regardless of review scope.'
    return result


def check(repo, name, command, timeout=120, env_vars=None):
    if not command or timeout <= 0:
        raise ValueError('Provide a command and a positive timeout.')
    root = os.fsdecode(git(repo, 'rev-parse', '--show-toplevel')).strip()
    start = time.monotonic()
    result = {'name': name, 'command': command, 'cwd': root,
              'execution_scope': 'current worktree', 'status': 'ERROR', 'exit_code': None}
    proc_env = os.environ.copy()
    if env_vars:
        for item in env_vars:
            if '=' in item:
                k, v = item.split('=', 1)
                proc_env[k] = v
    # Temporary files avoid pipe deadlocks and unbounded memory for noisy checks.
    with tempfile.TemporaryFile() as output:
        try:
            proc = subprocess.Popen(command, cwd=root, stdout=output, stderr=subprocess.STDOUT,
                                    env=proc_env, start_new_session=(os.name == 'posix'))
            try:
                result['exit_code'] = proc.wait(timeout=timeout)
                result['status'] = 'PASS' if proc.returncode == 0 else 'FAIL'
            except subprocess.TimeoutExpired:
                if os.name == 'posix':
                    os.killpg(proc.pid, signal.SIGKILL)
                else:
                    proc.kill()
                proc.wait()
                result['status'] = 'TIMEOUT'
            output.seek(0)
            data = output.read(16001)
            result['output'] = data[:16000].decode(errors='replace')
            result['output_truncated'] = len(data) > 16000
        except OSError as exc:
            result['error'] = str(exc)
    result['seconds'] = round(time.monotonic() - start, 3)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    c = sub.add_parser('collect')
    c.add_argument('--repo', default='.')
    c.add_argument('--scope', choices=['all', 'staged', 'working', 'branch'], default='all')
    c.add_argument('--base')
    c.add_argument('--commit-policy', choices=['off', 'conventional', 'ticket-or-conventional'], default='off')
    c.add_argument('--rules', action='append', default=[], help='Filter rules.md by header substring')
    r = sub.add_parser('check')
    r.add_argument('--repo', default='.')
    r.add_argument('--name', required=True)
    r.add_argument('--timeout', type=float, default=120)
    r.add_argument('--env', action='append', default=[], help='Environment variable KEY=VALUE')
    r.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.action == 'collect':
            result = collect(args.repo, args.scope, args.base, rules_filters=args.rules, commit_policy=args.commit_policy)
            code = 1 if result['conflicts'] else 0
        else:
            command = args.command[1:] if args.command[:1] == ['--'] else args.command
            result = check(args.repo, args.name, command, args.timeout, env_vars=args.env)
            code = 0 if result['status'] == 'PASS' else 1
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        result, code = {'status': 'ERROR', 'error': str(exc)}, 2
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
