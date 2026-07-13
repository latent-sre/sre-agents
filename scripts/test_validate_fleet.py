#!/usr/bin/env python3
"""Tests for scripts/validate_fleet.py.

The validator is the fleet's only structural gate, and until now it had no tests. That is not a
cosmetic gap: three of its checks were passing on inputs they exist to reject, and the worst one
silently removed a security control. Each test below mutates a throwaway copy of the real fleet in
exactly one way and asserts the validator rejects it -- so a check that stops checking fails here
instead of shipping.

Run:  python3 -m unittest discover -s scripts -p 'test_*.py' -v
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDATOR = os.path.join(REPO, 'scripts', 'validate_fleet.py')
IGNORE = shutil.ignore_patterns('.git', '__pycache__', '*.pyc', '.probe-tmp')


def copy_fleet(dest):
    """A throwaway copy of the whole repo. The validator reads .claude/ AND the roster docs
    (README.md, AGENTS.md, docs/), so a partial copy would fail for the wrong reason."""
    shutil.copytree(REPO, dest, ignore=IGNORE, dirs_exist_ok=True)
    return dest


def run_validator(root):
    """Run the real validator against `root`. Returns (returncode, combined output)."""
    env = dict(os.environ, FLEET_ROOT=root)
    p = subprocess.run(
        [sys.executable, VALIDATOR],
        capture_output=True, text=True, env=env, cwd=root,
    )
    return p.returncode, (p.stdout or '') + (p.stderr or '')


class FleetFixture(unittest.TestCase):
    """Base: gives each test an isolated copy of the fleet at self.root."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix='fleet-')
        self.root = copy_fleet(os.path.join(self._tmp, 'repo'))

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def agent(self, name):
        return os.path.join(self.root, '.claude', 'agents', name + '.md')

    def skill(self, name):
        return os.path.join(self.root, '.claude', 'skills', name, 'SKILL.md')

    def edit(self, path, old, new, count=1):
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
        self.assertIn(old, text, "fixture precondition: %r not found in %s" % (old, path))
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(text.replace(old, new, count))

    def assertRejected(self, needle):
        rc, out = run_validator(self.root)
        self.assertNotEqual(rc, 0, "validator PASSED but should have failed.\n%s" % out)
        self.assertRegex(out, needle)

    def assertAccepted(self):
        rc, out = run_validator(self.root)
        self.assertEqual(rc, 0, "validator FAILED on an unmutated fleet:\n%s" % out)


class TestSeam(FleetFixture):
    """The validator must be pointable at a root other than its own repo, or it cannot be tested
    at all -- which is why it never was."""

    def test_unmutated_fleet_passes(self):
        self.assertAccepted()

    def test_validator_validates_the_root_it_is_given(self):
        # Break the fixture in a way the validator ALREADY knows how to catch. If it reports this,
        # it is reading the fixture. If it passes, it is still reading its own repo and every other
        # test in this file would be meaningless.
        os.remove(self.skill('merge-gate'))
        self.assertRejected(r"merge-gate.*missing SKILL\.md")


GUARDED = ('code-reviewer', 'security-reviewer', 'sre-engineer')


class TestUnknownFrontmatterKeys(FleetFixture):
    """Claude Code SILENTLY IGNORES an unrecognised frontmatter key. So a typo does not error --
    it deletes whatever that key configured. On these agents the key it deletes is `hooks:`, which
    is the ONLY thing making a Bash-holding agent read-only."""

    def test_misspelled_hooks_key_is_rejected(self):
        # The whole reason this file exists. `hooks:` -> `hook:` on a read-only Bash agent removes
        # its guard, and the validator used to say VALIDATION: PASS.
        self.edit(self.agent('code-reviewer'), '\nhooks:\n', '\nhook:\n')
        self.assertRejected(r"code-reviewer.*(unknown|unrecognis|unrecogniz).*'?hook'?")

    def test_unknown_agent_key_is_rejected(self):
        self.edit(self.agent('sre-engineer'), '\nname:', '\nmdoel: opus\nname:')
        self.assertRejected(r"sre-engineer.*(unknown|unrecognis|unrecogniz).*'?mdoel'?")

    def test_unknown_skill_key_is_rejected(self):
        self.edit(self.skill('merge-gate'), '\nname:', '\nallowed-tolls: Read\nname:')
        self.assertRejected(r"merge-gate.*(unknown|unrecognis|unrecogniz).*'?allowed-tolls'?")

    def test_nested_hook_config_keys_are_not_mistaken_for_top_level_keys(self):
        # `matcher:`, `type:`, `command:` live INSIDE hooks:. A key check that isn't anchored to
        # column zero would reject the real fleet. Guards against overshooting the fix.
        self.assertAccepted()


class TestGuardWiring(FleetFixture):
    """The guard check was `re.search(r'readonly-guard(-hook\\.sh|\\.py)', body)` -- a substring grep
    over the WHOLE FILE. It proves the string appears somewhere, not that the hook is wired."""

    def _strip_hooks_block(self, path):
        """Delete the top-level `hooks:` block from the frontmatter, leaving everything else."""
        with open(path, encoding='utf-8') as fh:
            lines = fh.read().split('\n')
        fences = [i for i, ln in enumerate(lines) if ln.strip() == '---'][:2]
        start = next(i for i in range(fences[0], fences[1]) if lines[i].startswith('hooks:'))
        end = start + 1
        while end < fences[1] and (lines[end].startswith((' ', '\t')) or not lines[end].strip()):
            end += 1
        del lines[start:end]
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write('\n'.join(lines))

    def test_guard_block_deleted_is_rejected_even_though_body_still_says_readonly_guard(self):
        # The exact blind spot of a substring grep: the hook is GONE, but the agent's prose still
        # discusses the guard, so the old check was satisfied and the agent shipped unguarded.
        path = self.agent('code-reviewer')
        self._strip_hooks_block(path)
        with open(path, 'a', encoding='utf-8', newline='') as fh:
            fh.write('\n\nMy Bash access is constrained by scripts/readonly-guard.py.\n')
        self.assertRejected(r"code-reviewer.*(guard|hook)")

    def test_guard_hook_with_a_non_bash_matcher_is_rejected(self):
        # Guard only fires on the tool it matches. Matching Read leaves Bash wide open.
        self.edit(self.agent('security-reviewer'), 'matcher: Bash', 'matcher: Read')
        self.assertRejected(r"security-reviewer.*(guard|matcher|Bash)")

    def test_guard_hook_pointing_at_a_missing_script_is_rejected(self):
        # A hook whose command does not exist fails open: no guard, no error, nothing logged.
        # Note the path still CONTAINS 'readonly-guard-hook.sh', so the old substring grep is
        # perfectly happy with it. Only actually resolving the path catches this.
        self.edit(self.agent('sre-engineer'),
                  '/scripts/readonly-guard-hook.sh',
                  '/scripts/nonexistent/readonly-guard-hook.sh')
        self.assertRejected(r"sre-engineer.*(not found|does not exist|missing|no such)")


class TestPreloadedSkillsList(FleetFixture):
    """`skills:` preloads a skill's content at startup. Its VALUES were never validated, so a typo
    silently preloads nothing -- the agent just quietly loses the knowledge it was given."""

    def test_skills_entry_that_does_not_resolve_is_rejected(self):
        self.edit(self.agent('code-reviewer'), '  - merge-gate', '  - merge-gait')
        self.assertRejected(r"code-reviewer.*merge-gait")

    def test_preloading_a_disable_model_invocation_skill_is_rejected(self):
        # A skill with disable-model-invocation: true CANNOT be preloaded -- "preloading draws from
        # the same set of skills Claude can invoke" (code.claude.com/docs/en/sub-agents). Listing one
        # is a silent no-op. pcf-deploy is such a skill in this fleet.
        self.edit(self.agent('code-reviewer'), '  - merge-gate', '  - merge-gate\n  - pcf-deploy')
        self.assertRejected(r"code-reviewer.*pcf-deploy")


if __name__ == '__main__':
    unittest.main()
