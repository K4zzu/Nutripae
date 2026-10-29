from nutripae.balance import Porcion, evaluar
from nutripae.foods import grupo_de


def p(alimento, gramos, apto=True):
    from nutripae.foods import catalogo
    nombre, grupo = catalogo().get(alimento, (alimento, "otro"))
    return Porcion(alimento, nombre, grupo, gramos, apto)


def test_grupo_de_mapea_cereal_y_tuberculo_a_energetico():
    assert grupo_de("arroz_blanco") == "energetico" and grupo_de("papa_cocida") == "energetico"
    assert grupo_de("sancocho") == "otro"


def test_plato_balanceado_es_verde():
    v = evaluar([p("pollo_guisado", 90), p("arroz_blanco", 90), p("ensalada_fresca", 100), p("banano", 80), p("jugo_natural", 200)], "primaria")
    assert v.semaforo == "verde" and v.razon_grupo is None
    assert v.total_g == 360  # la bebida no cuenta


def test_falta_verdura_es_rojo_con_razon_verdura():
    v = evaluar([p("pollo_guisado", 90), p("arroz_blanco", 90), p("banano", 80)], "primaria")
    assert v.semaforo == "rojo" and (v.razon_grupo, v.razon_tipo) == ("verdura", "falta")
    assert any(x.grupo == "verdura" and x.estado == "falta" and x.gramos == 0 for x in v.porciones)


def test_proteina_corta_es_amarillo():
    v = evaluar([p("pollo_guisado", 20), p("arroz_blanco", 120), p("ensalada_fresca", 100), p("banano", 80)], "primaria")
    assert v.semaforo == "amarillo" and (v.razon_grupo, v.razon_tipo) == ("proteina", "corto")


def test_casi_todo_arroz_es_amarillo_excedido():
    v = evaluar([p("pollo_guisado", 70), p("arroz_blanco", 300), p("ensalada_fresca", 80), p("banano", 80)], "primaria")
    assert v.semaforo == "amarillo" and v.razon_tipo == "excedido" and v.razon_grupo == "energetico"


def test_no_apto_es_rojo_y_prioriza_falta():
    v = evaluar([p("pollo_guisado", 90, apto=False), p("arroz_blanco", 90), p("ensalada_fresca", 100)], "primaria")
    assert v.semaforo == "rojo" and v.razon_tipo == "falta" and v.razon_grupo == "fruta"


def test_plato_muy_pequeno_es_amarillo():
    v = evaluar([p("pollo_guisado", 30), p("arroz_blanco", 30), p("ensalada_fresca", 40), p("banano", 30)], "secundaria")
    assert v.semaforo == "amarillo" and v.razon_tipo == "pequeno"


def test_alimento_desconocido_entra_como_otro_sin_nutrientes():
    v = evaluar([p("sancocho", 200), p("pollo_guisado", 90), p("arroz_blanco", 90), p("ensalada_fresca", 100), p("banano", 80)], "primaria")
    assert any(x.alimento == "sancocho" and x.grupo == "otro" for x in v.porciones)
    assert v.nutrientes["kcal"] > 0


def test_porciones_repetidas_suman_sus_nutrientes():
    base = [p("pollo_guisado", 90), p("arroz_blanco", 90), p("ensalada_fresca", 100)]
    dos = evaluar(base + [p("banano", 40), p("banano", 40)], "primaria")
    una = evaluar([p("pollo_guisado", 90), p("arroz_blanco", 90), p("ensalada_fresca", 100), p("banano", 80)], "primaria")
    assert dos.nutrientes == una.nutrientes
