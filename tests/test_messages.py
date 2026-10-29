from nutripae.balance import Porcion, Veredicto, evaluar
from nutripae.messages import RAZON, VERDE, mensaje

PALABRAS_PROHIBIDAS = ["modelo", "api", "segment", "clave", "proveedor", "demo"]


def test_verde_usa_nombre_y_frase_variada():
    v = evaluar([Porcion("pollo_guisado", "Pollo", "proteina", 90), Porcion("arroz_blanco", "Arroz", "energetico", 90),
                 Porcion("ensalada_fresca", "Ensalada", "verdura", 100), Porcion("banano", "Banano", "fruta", 80)], "primaria")
    t1, d1 = mensaje(v, "Juan", semilla=1)
    t2, d2 = mensaje(v, "Juan", semilla=2)
    assert t1 == "¡Listo, Juan! Tu plato está balanceado." and d1 in VERDE["ninos"] and d1 != d2
    assert mensaje(v, "Juan", grado="secundaria", semilla=1)[1] in VERDE["adolescentes"]


def test_falta_verdura_explica_por_que():
    v = evaluar([Porcion("pollo_guisado", "Pollo", "proteina", 90), Porcion("arroz_blanco", "Arroz", "energetico", 90),
                 Porcion("banano", "Banano", "fruta", 80)], "primaria")
    t, d = mensaje(v, None)
    assert t == "Espera. Hay que cambiar tu plato." and d == "Te falta verdura. La verdura te ayuda a crecer fuerte."


def test_sin_jerga():
    v = evaluar([], "primaria")
    for texto in mensaje(v, "Ana"):
        assert not any(w in texto.lower() for w in PALABRAS_PROHIBIDAS)


def test_listas_verde_suficientes_y_sin_jerga():
    for lista in VERDE.values():
        assert len(lista) >= 6
        for frase in lista:
            assert not any(w in frase.lower() for w in PALABRAS_PROHIBIDAS)
    for frase in RAZON.values():
        assert not any(w in frase.lower() for w in PALABRAS_PROHIBIDAS)


def test_energetico_usa_palabras_de_nino():
    v = evaluar([Porcion("pollo_guisado", "Pollo", "proteina", 90), Porcion("ensalada_fresca", "Ensalada", "verdura", 100),
                 Porcion("banano", "Banano", "fruta", 80)], "primaria")
    t, d = mensaje(v, "Ana")
    assert t == "Espera, Ana. Hay que cambiar tu plato."
    assert d == "Te falta arroz, papa o plátano. El arroz, la papa y el plátano te dan energía para jugar y estudiar."


def test_corto_amarillo():
    v = Veredicto("amarillo", "verdura", "corto", [], 300, {}, {})
    t, d = mensaje(v, "Luis")
    assert t == "Casi, Luis. Vuelve a la fila y completa tu plato."
    assert d == "Te falta un poco más de verdura. La verdura te ayuda a crecer fuerte."


def test_no_apto_nombra_el_alimento():
    v = Veredicto("rojo", "proteina", "no_apto",
                  [Porcion("a", "Arroz", "energetico", 90),
                   Porcion("p", "Pollo", "proteina", 90, apto=False, estado="no_apto")],
                  180, {}, {})
    assert mensaje(v, None)[1] == "Pollo no se ve bien. Pide que te lo cambien."


def test_excedido_explica_el_grupo_mas_corto():
    props = {"verdura_fruta": 0.1, "proteina": 0.25, "energetico": 0.65}
    v = Veredicto("amarillo", "energetico", "excedido", [], 400, props, {})
    d = mensaje(v, None)[1]
    assert d == "Tienes mucho arroz, papa o plátano y poco de lo demás. La verdura te ayuda a crecer fuerte."
    props = {"verdura_fruta": 0.5, "proteina": 0.05, "energetico": 0.45}
    v = Veredicto("amarillo", "energetico", "excedido", [], 400, props, {})
    assert mensaje(v, None)[1].endswith("La proteína construye tus músculos.")


def test_excedido_proteina_concuerda_en_genero():
    props = {"verdura_fruta": 0.2, "proteina": 0.6, "energetico": 0.2}
    v = Veredicto("amarillo", "proteina", "excedido", [], 400, props, {})
    assert mensaje(v, None)[1].startswith("Tienes mucha proteína y poco de lo demás.")


def test_pequeno():
    v = Veredicto("amarillo", None, "pequeno", [], 100, {}, {})
    assert mensaje(v, None)[1] == "Tu plato está muy pequeño. Pide un poco más de todo."
