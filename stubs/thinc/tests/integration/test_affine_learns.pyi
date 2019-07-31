# Stubs for thinc.tests.integration.test_affine_learns (Python 3)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from ...neural._classes.affine import Affine
from ...neural.optimizers import SGD
from typing import Any

def model(): ...
def test_init(model: Any) -> None: ...
def test_predict_bias(model: Any) -> None: ...
def test_predict_weights(X: Any, expected: Any) -> None: ...
def test_update() -> None: ...