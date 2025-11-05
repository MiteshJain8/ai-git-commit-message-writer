import os
import unittest
import importlib.util
import types
import sys
from types import SimpleNamespace

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'prepare-commit-msg.py')
SCRIPT_PATH = os.path.abspath(SCRIPT_PATH)


def load_hook_module():
    # Ensure a fake google.generativeai module exists for import if the SDK is not installed.
    if 'google' not in sys.modules:
        fake_google = types.ModuleType('google')
        sys.modules['google'] = fake_google
    if 'google.generativeai' not in sys.modules:
        fake_ga = types.ModuleType('google.generativeai')
        # provide a placeholder generate_content to be overridden by tests
        fake_ga.generate_content = lambda *a, **k: SimpleNamespace(text='')
        fake_ga.configure = lambda *a, **k: None
        sys.modules['google.generativeai'] = fake_ga

    spec = importlib.util.spec_from_file_location('prepare_commit_hook', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrepareCommitMsgTests(unittest.TestCase):
    def test_dry_run_generates_message(self):
        module = load_hook_module()

        # Patch environment key
        os.environ['GEMINI_API_KEY'] = 'test-key'

        # Mock subprocess.run to return a staged diff
        def fake_run(args, capture_output, text, check):
            return SimpleNamespace(returncode=0, stdout='diff --git a/foo.py b/foo.py\n+print("hello")\n')

        module.subprocess.run = fake_run

        # Mock generativeai.generate_content to return a simple text attribute
        def fake_generate_content(model, prompt, temperature, max_output_tokens):
            return SimpleNamespace(text='feat: add hello print\n\nAdd print statement to foo.py')

        module.generativeai.generate_content = fake_generate_content

        # Run the hook in dry-run mode (should return the generated message)
        message = module.run_hook('/tmp/nonexistent', commit_source=None, dry_run=True)
        self.assertIsNotNone(message)
        self.assertTrue(message.startswith('feat:'), 'Message should start with a Conventional Commits type')
        self.assertIn('hello', message)


if __name__ == '__main__':
    unittest.main()
