"""
Fighter profile read-model (FTR-01B1).

Read-only, independent of the XGBoost pipeline, the feature calculator,
``latest_features`` and ``backend/intelligence``.

Package name: the ticket asked for ``backend/profile/``, but a top-level
package called ``profile`` shadows the stdlib ``profile`` module and breaks
``import cProfile`` whenever ``backend/`` is first on sys.path (reproduced; see
test_profile_isolation.py::test_cprofile_still_importable...).  It is therefore
named ``fighter_profile``.
"""

from .service import (  # noqa: F401
    build_profile_extension, build_history, read_profile_inputs, guard_extension, validate_extension,
)
from .sanitize import sanitize_raw_stats, json_safe  # noqa: F401
