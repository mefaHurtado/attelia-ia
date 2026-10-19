import pytest
pytest.importorskip("langchain_core")
from app.services.documentos import extraer_texto


def test_extraer_txt_y_markdown():
    assert extraer_texto("nota.txt", b"moda y estilo") == "moda y estilo"
    assert extraer_texto("notas.md", b"# Colores\nAzul y blanco") == "# Colores\nAzul y blanco"


def test_rechazar_extension_no_permitida():
    with pytest.raises(ValueError):
        extraer_texto("malware.exe", b"contenido")
