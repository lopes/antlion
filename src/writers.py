from collections.abc import Callable
from pathlib import Path

from src.write_conf import write_conf
from src.write_docx import write_docx
from src.write_epdf import write_epdf
from src.write_json import write_json
from src.write_md import write_md
from src.write_pdf import write_pdf
from src.write_pptx import write_pptx
from src.write_xlsx import write_xlsx
from src.write_xml import write_xml

_WRITERS: dict[str, Callable[..., None]] = {
    "md": write_md,
    "json": write_json,
    "xml": write_xml,
    "conf": write_conf,
    "pdf": write_pdf,
    "epdf": write_epdf,
    "docx": write_docx,
    "xlsx": write_xlsx,
    "pptx": write_pptx,
}


def get_writer(fmt: str) -> Callable[..., None]:
    if fmt not in _WRITERS:
        raise ValueError(f"No writer for format: {fmt}")
    return _WRITERS[fmt]
