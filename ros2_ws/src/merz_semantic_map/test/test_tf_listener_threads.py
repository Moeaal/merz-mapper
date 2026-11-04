"""Static check, runs anywhere: a node that waits for TF inside a callback must give its listener its own thread.

rclpy's TransformListener defaults to spin_thread=False, so its TF subscriptions are served by the node's own executor.
A lookup_transform(..., timeout=...) inside a callback of a single-threaded node then blocks the only thread that could
deliver the transform it is waiting for. The lookup always uses its full timeout and fails whenever the transform at the
requested time had not already arrived.
"""
import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / 'merz_semantic_map'


def _calls(tree: ast.AST, name: str) -> list[ast.Call]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call)
            and getattr(node.func, 'attr', getattr(node.func, 'id', None)) == name]


def _keyword(call: ast.Call, name: str):
    return next((kw.value for kw in call.keywords if kw.arg == name), None)


def test_blocking_tf_lookups_have_a_listener_with_its_own_thread():
    checked = 0
    for path in sorted(PACKAGE.glob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        if not any(_keyword(call, 'timeout') is not None for call in _calls(tree, 'lookup_transform')):
            continue
        checked += 1
        listeners = _calls(tree, 'TransformListener')
        assert listeners, f'{path.name} waits for TF but creates no TransformListener'
        for listener in listeners:
            spin_thread = _keyword(listener, 'spin_thread')
            assert isinstance(spin_thread, ast.Constant) and spin_thread.value is True, (
                f'{path.name}:{listener.lineno} waits for TF in a callback, so its TransformListener needs '
                'spin_thread=True')
    assert checked, 'positive control: landmark_node.py waits for TF, so at least one file must have been checked'
