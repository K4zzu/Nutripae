from nutripae.fuse import cruzar
from nutripae.segment import Region
from nutripae.vision import Deteccion


def det(alimento, bbox, nombre="x"):
    return Deteccion(alimento, nombre, 80, bbox, .9, True, "")


def reg(bbox):
    x1, y1, x2, y2 = bbox
    return Region([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], bbox, (x2 - x1) * (y2 - y1))


def test_asigna_region_con_mayor_solape():
    porciones = cruzar([det("arroz_blanco", (0, 0, .5, .5))], [reg((.05, .05, .45, .45)), reg((.6, .6, .9, .9))])
    assert len(porciones) == 1 and porciones[0].poligono[0] == (.05, .05) and not porciones[0].aproximado


def test_sin_region_usa_bbox_aproximado():
    p = cruzar([det("banano", (.6, .6, .9, .9))], [])[0]
    assert p.aproximado and p.poligono == [(.6, .6), (.9, .6), (.9, .9), (.6, .9)]


def test_region_no_se_reutiliza():
    ps = cruzar([det("arroz_blanco", (0, 0, .5, .5)), det("pollo_guisado", (0, 0, .5, .5))], [reg((.1, .1, .4, .4))])
    assert sum(1 for p in ps if not p.aproximado) == 1


def test_otro_conserva_nombre_real():
    p = cruzar([det("otro", (0, 0, .5, .5), nombre="Sancocho")], [])[0]
    assert p.grupo == "otro" and p.nombre == "Sancocho"


def test_centroide_fuera_del_bbox_no_es_candidata():
    p = cruzar([det("banano", (0, 0, .3, .3))], [reg((.5, .5, .9, .9))])[0]
    assert p.aproximado


def test_empate_de_iou_gana_la_region_mas_grande():
    chica = Region([(0, 0), (.2, 0), (.2, .2), (0, .2)], (0, 0, .2, .2), .04)
    grande = Region([(0, 0), (.2, 0), (.2, .2), (0, .2)], (0, 0, .2, .2), .05)
    p = cruzar([det("banano", (0, 0, .4, .4))], [chica, grande])[0]
    assert not p.aproximado


def test_copia_campos_de_la_deteccion():
    d = Deteccion("banano", "Banano", 120, (0, 0, .5, .5), .9, False, "crudo")
    p = cruzar([d], [])[0]
    assert (p.gramos, p.apto, p.observacion, p.bbox, p.nombre) == (120, False, "crudo", (0, 0, .5, .5), "Banano")
