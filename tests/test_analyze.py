import threading, time, pytest
from PIL import Image
from nutripae.analyze import Analizador, PersonaDetectada, Ocupado
from nutripae.vision import VisionDemo, ResultadoVision
from nutripae.segment import SegmentadorElipses
from nutripae.balance import UMBRALES_INICIALES
from nutripae import db, verificaciones

class VisionPersona:
    def analizar(self, imagen): return ResultadoVision([], persona=True)

class VisionLenta(VisionDemo):
    def analizar(self, imagen): time.sleep(0.5); return super().analizar(imagen)

def conectar(settings):
    con = db.conectar(settings.db_path)
    con.execute("insert into usuarios(usuario,nombre,hash) values('u','U','x')")
    return con

def analizador(vision=None, espera=20):
    return Analizador(vision or VisionDemo("completa", 1), SegmentadorElipses(), UMBRALES_INICIALES, espera_s=espera)

def test_persona_descarta_la_toma():
    with pytest.raises(PersonaDetectada):
        analizador(VisionPersona()).analizar(Image.new("RGB", (640, 480)), "primaria", "Ana")

def test_demo_completa_da_verde_con_poligonos():
    a = analizador().analizar(Image.new("RGB", (640, 480)), "primaria", "Ana")
    assert a.veredicto.semaforo == "verde" and all(p.poligono for p in a.veredicto.porciones) and a.titulo.startswith("¡Listo, Ana!")

def test_segundo_analisis_simultaneo_espera_o_falla():
    a = analizador(VisionLenta("completa", 1), espera=0.1)
    errores = []
    def run():
        try: a.analizar(Image.new("RGB", (64, 48)), "primaria", None)
        except Ocupado: errores.append(1)
    hilos = [threading.Thread(target=run) for _ in range(2)]; [h.start() for h in hilos]; [h.join() for h in hilos]
    assert errores == [1]

def test_sin_consentimiento_no_guarda_nombre_ni_foto(settings):
    con = conectar(settings)
    con.execute("insert into estudiantes(codigo,nombre,grado,grupo,sede,orden,consentimiento) values('E1','Ana','primaria','3-A','IE Santa Librada',1,0)")
    est = db.estudiante(con, 1)
    a = analizador().analizar(Image.new("RGB", (640, 480)), "primaria", "Ana")
    vid = verificaciones.guardar(con, settings, a, estudiante=est, sede="IE Santa Librada", grado="primaria", usuario_id=1, modo="camara")
    fila = con.execute("select estudiante_id, foto from verificaciones where id=?", (vid,)).fetchone()
    assert fila["estudiante_id"] is None and fila["foto"] is None and not list(settings.fotos_dir.rglob("*.jpg"))

def test_con_consentimiento_guarda_foto_y_muestra(settings):
    con = conectar(settings)
    con.execute("insert into estudiantes(codigo,nombre,grado,grupo,sede,orden,consentimiento) values('E1','Ana','primaria','3-A','IE Santa Librada',1,1)")
    a = analizador().analizar(Image.new("RGB", (640, 480)), "primaria", "Ana")
    vid = verificaciones.guardar(con, settings, a, estudiante=db.estudiante(con, 1), sede="IE Santa Librada", grado="primaria", usuario_id=1, modo="camara")
    fila = con.execute("select estudiante_id, foto from verificaciones where id=?", (vid,)).fetchone()
    assert fila["estudiante_id"] == 1 and (settings.fotos_dir / fila["foto"]).exists()
    assert con.execute("select count(*) from fotos_entrenamiento").fetchone()[0] == 1

def test_corregir_reevalua_y_registra(settings):
    con = conectar(settings)
    a = analizador(VisionDemo("falta_grupo", 1)).analizar(Image.new("RGB", (640, 480)), "primaria", None)
    vid = verificaciones.guardar(con, settings, a, estudiante=None, sede="S", grado="primaria", usuario_id=1, modo="camara")
    idx = next(i for i, p in enumerate(a.veredicto.porciones) if p.estado != "falta")
    v2 = verificaciones.corregir(con, vid, idx, "ensalada_fresca", usuario_id=1)
    assert con.execute("select count(*) from correcciones").fetchone()[0] == 1
    assert con.execute("select corregida from verificaciones where id=?", (vid,)).fetchone()[0] == 1

def test_demo_no_guarda_foto_ni_estudiante(settings):
    con = conectar(settings)
    con.execute("insert into estudiantes(codigo,nombre,grado,grupo,sede,orden,consentimiento) values('E1','Ana','primaria','3-A','S',1,1)")
    a = analizador().analizar(Image.new("RGB", (640, 480)), "primaria", "Ana")
    vid = verificaciones.guardar(con, settings, a, estudiante=db.estudiante(con, 1), sede="S", grado="primaria", usuario_id=1, modo="demo")
    fila = con.execute("select estudiante_id, foto, modo from verificaciones where id=?", (vid,)).fetchone()
    assert fila["estudiante_id"] is None and fila["foto"] is None and fila["modo"] == "demo"
    assert not list(settings.fotos_dir.rglob("*.jpg"))

def test_tarjeta_activa_devuelve_estudiante(settings):
    con = conectar(settings)
    con.execute("insert into estudiantes(codigo,nombre,grado,grupo,sede,orden,consentimiento) values('E1','Ana','primaria','3-A','S',1,1)")
    con.execute("insert into tarjetas(codigo,estudiante_id,activa) values('T1',1,1),('T2',1,0)")
    assert db.estudiante_por_tarjeta(con, "T1")["nombre"] == "Ana"
    assert db.estudiante_por_tarjeta(con, "T2") is None
    assert db.estudiante(con, 99) is None
