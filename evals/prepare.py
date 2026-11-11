#!/usr/bin/env python3
"""Create two isolated, synthetic review repositories. Never uses production code."""
import argparse
from pathlib import Path
import subprocess

BASE = '''def discount(total, percent):
    if total < 0 or not 0 <= percent <= 100:
        raise ValueError("invalid amount or percentage")
    return total * (100 - percent) / 100
'''
TEST = '''import unittest
from pricing import discount

class PricingTests(unittest.TestCase):
    def test_regular_discount(self):
        self.assertEqual(discount(100, 10), 90)
    def test_negative_total(self):
        with self.assertRaises(ValueError):
            discount(-1, 10)
'''

def prepare(parent):
    for name in ('case-a', 'case-b'):
        root = parent / name
        root.mkdir(parents=True, exist_ok=False)
        def git(*args):
            subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)
        git('init', '-b', 'main')
        git('config', 'user.name', 'Evaluation')
        git('config', 'user.email', 'eval@example.invalid')
        (root / 'pricing.py').write_text(BASE)
        (root / 'test_pricing.py').write_text(TEST)
        (root / 'AGENTS.md').write_text('Required local check: python3 -m unittest -v. No remote CI jobs.\nContract: discount accepts 0 through 100 percent, inclusive.\n')
        git('add', '.')
        git('commit', '-m', 'baseline')
        git('checkout', '-b', 'proposal')
        if name == 'case-a':
            (root / 'pricing.py').write_text(BASE.replace('percent <= 100', 'percent < 100'))
        else:
            (root / 'pricing.py').write_text(BASE.replace('def discount(total, percent):', 'def discount(total, percent):\n    """Apply a percentage discount to a nonnegative total."""'))
        print(root)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    prepare(parser.parse_args().destination.resolve())
