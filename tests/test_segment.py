import os
import pytest
from PIL import Image
from nutripae.segment import SegmentadorElipses, area_poligono, FastSAMSegmentador


def test_area_poligono_cuadrado():
    assert abs(area_poligono([(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5)]) - 0.25) < 1e-9


def test_elipses_una_por_bbox_dentro_del_bbox():
    regs = SegmentadorElipses().segmentar_desde([(0.1, 0.1, 0.5, 0.5), (0.6, 0.6, 0.9, 0.9)])
    assert len(regs) == 2 and all(0.1 <= x <= 0.5 and 0.1 <= y <= 0.5 for x, y in regs[0].poligono)


@pytest.mark.skipif(not os.getenv("NUTRIPAE_TEST_FASTSAM"), reason="descarga pesos; ejecutar con NUTRIPAE_TEST_FASTSAM=1")
def test_fastsam_segmenta_bandeja_sintetica():
    from nutripae.vision import VisionDemo
    try:
        from nutripae.overlay import bandeja_sintetica  # Tarea 7
    except ImportError:
        from nutripae.detector import bandeja_sintetica  # v1, misma firma
    img = bandeja_sintetica(VisionDemo("completa", 1).analizar(Image.new("RGB", (900, 600))).detecciones)
    regs = FastSAMSegmentador().segmentar(img)
    assert 3 <= len(regs) <= 40


def test_crear_segmentador_y_valor_invalido():
    from types import SimpleNamespace
    from nutripae.segment import crear_segmentador
    assert isinstance(crear_segmentador(SimpleNamespace(segmentador="fastsam")), FastSAMSegmentador)
    assert isinstance(crear_segmentador(SimpleNamespace(segmentador="demo")), SegmentadorElipses)
    with pytest.raises(ValueError):
        crear_segmentador(SimpleNamespace(segmentador="otro"))
