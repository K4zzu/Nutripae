from PIL import Image
from nutripae.overlay import anotar, reducir
from nutripae.balance import Porcion


def test_reducir_respeta_lado_mayor():
    assert max(reducir(Image.new("RGB", (4000, 3000)), 1024).size) == 1024


def test_anotar_pinta_el_poligono_con_el_color_del_grupo():
    img = Image.new("RGB", (200, 200), "black")
    out = anotar(img, [Porcion("ensalada_fresca", "Ensalada", "verdura", 80, poligono=[(.1,.5),(.9,.5),(.9,.9),(.1,.9)])])
    r, g, b = out.getpixel((100, 160))
    assert g > r and g > b  # verde
    assert out.getpixel((100, 20)) == (0, 0, 0)
