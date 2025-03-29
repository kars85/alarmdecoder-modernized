from __future__ import annotations

import warnings

from pathlib import Path

from .. import _types as _t
from .._log import log as parent_log
from .._version_cls import _version_as_tuple
from ..version import ScmVersion

log = parent_log.getChild("dump_version")

TEMPLATES = {
    ".py": """\
# file generated by setuptools-scm
# don't change, don't track in version control

__all__ = ["__version__", "__version_tuple__", "version", "version_tuple"]

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Tuple
    from typing import Union

    VERSION_TUPLE = Tuple[Union[int, str], ...]
else:
    VERSION_TUPLE = object

version: str
__version__: str
__version_tuple__: VERSION_TUPLE
version_tuple: VERSION_TUPLE

__version__ = version = {version!r}
__version_tuple__ = version_tuple = {version_tuple!r}
""",
    ".txt": "{version}",
}


def dump_version(
    root: _t.PathT,
    version: str,
    write_to: _t.PathT,
    template: str | None = None,
    scm_version: ScmVersion | None = None,
) -> None:
    assert isinstance(version, str)
    root = Path(root)
    write_to = Path(write_to)
    if write_to.is_absolute():
        # trigger warning on escape
        write_to.relative_to(root)
        warnings.warn(
            f"{write_to=!s} is a absolute path,"
            " please switch to using a relative version file",
            DeprecationWarning,
        )
        target = write_to
    else:
        target = Path(root).joinpath(write_to)
    write_version_to_path(
        target, template=template, version=version, scm_version=scm_version
    )


def _validate_template(target: Path, template: str | None) -> str:
    if template == "":
        warnings.warn(f"{template=} looks like a error, using default instead")
        template = None
    if template is None:
        template = TEMPLATES.get(target.suffix)

    if template is None:
        raise ValueError(
            f"bad file format: {target.suffix!r} (of {target})\n"
            "only *.txt and *.py have a default template"
        )
    else:
        return template


def write_version_to_path(
    target: Path, template: str | None, version: str, scm_version: ScmVersion | None
) -> None:
    final_template = _validate_template(target, template)
    log.debug("dump %s into %s", version, target)
    version_tuple = _version_as_tuple(version)
    if scm_version is not None:
        content = final_template.format(
            version=version,
            version_tuple=version_tuple,
            scm_version=scm_version,
        )
    else:
        content = final_template.format(version=version, version_tuple=version_tuple)

    target.write_text(content, encoding="utf-8")
