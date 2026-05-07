"""
Orquestador Ruta-Óptima: crea la BD en disco (ruta dinámica con os), semilla datos
y expone un menú interactivo con validaciones.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import traceback
from typing import Callable, List, Optional, Tuple

from datos import DESTINOS_INICIALES, PAQUETES_INICIALES
from destinos import Destino, RepositorioDestinos
from envios import CalculadoraCostoEnvio
from manifiestos import Manifiesto, RepositorioManifiestos
from paquetes import ClasificadorPaquetes, Paquete, RepositorioPaquetes


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "ruta_optima.db")


def _conectar() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_esquema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS destinos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            ciudad TEXT NOT NULL,
            zona TEXT NOT NULL,
            factor_costo REAL NOT NULL CHECK (factor_costo > 0)
        );

        CREATE TABLE IF NOT EXISTS manifiestos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            titulo TEXT NOT NULL,
            creado_en TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS paquetes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referencia TEXT NOT NULL UNIQUE,
            peso_kg REAL NOT NULL CHECK (peso_kg >= 0),
            destino_id INTEGER NOT NULL,
            categoria TEXT NOT NULL,
            costo_envio_cop REAL NOT NULL CHECK (costo_envio_cop >= 0),
            manifiesto_id INTEGER,
            creado_en TEXT NOT NULL,
            FOREIGN KEY (destino_id) REFERENCES destinos(id),
            FOREIGN KEY (manifiesto_id) REFERENCES manifiestos(id)
        );

        CREATE INDEX IF NOT EXISTS ix_paquetes_destino ON paquetes(destino_id);
        CREATE INDEX IF NOT EXISTS ix_paquetes_manifiesto ON paquetes(manifiesto_id);

        CREATE VIEW IF NOT EXISTS v_paquetes_analitica AS
        SELECT
            p.id AS paquete_id,
            p.referencia,
            p.peso_kg,
            p.categoria,
            p.costo_envio_cop,
            p.creado_en,
            strftime('%Y-%m-%d', p.creado_en) AS fecha_dia,
            strftime('%Y-%m', p.creado_en) AS fecha_mes,
            d.codigo AS destino_codigo,
            d.ciudad,
            d.zona,
            d.factor_costo,
            CASE WHEN p.manifiesto_id IS NULL THEN 'Pendiente' ELSE 'Asignado' END AS estado_manifiesto
        FROM paquetes p
        JOIN destinos d ON d.id = p.destino_id;

        CREATE VIEW IF NOT EXISTS v_resumen_categoria AS
        SELECT
            categoria,
            COUNT(*) AS cantidad_paquetes,
            SUM(peso_kg) AS peso_total_kg,
            SUM(costo_envio_cop) AS costo_total_cop
        FROM paquetes
        GROUP BY categoria;

        CREATE VIEW IF NOT EXISTS v_resumen_zona AS
        SELECT
            d.zona,
            COUNT(p.id) AS cantidad_paquetes,
            SUM(p.peso_kg) AS peso_total_kg,
            AVG(p.costo_envio_cop) AS costo_promedio_cop
        FROM paquetes p
        JOIN destinos d ON d.id = p.destino_id
        GROUP BY d.zona;

        CREATE VIEW IF NOT EXISTS v_manifiesto_resumen AS
        SELECT
            m.id AS manifiesto_id,
            m.codigo,
            m.titulo,
            m.creado_en,
            COUNT(p.id) AS num_paquetes,
            COALESCE(SUM(p.peso_kg), 0) AS peso_total_kg,
            COALESCE(SUM(p.costo_envio_cop), 0) AS costo_total_cop
        FROM manifiestos m
        LEFT JOIN paquetes p ON p.manifiesto_id = m.id
        GROUP BY m.id;
        """
    )
    conn.commit()


def semillar_si_vacio(
    conn: sqlite3.Connection,
    repo_d: RepositorioDestinos,
    repo_p: RepositorioPaquetes,
    clasificador: ClasificadorPaquetes,
    calculadora: CalculadoraCostoEnvio,
) -> None:
    if repo_d.listar():
        return
    for d in DESTINOS_INICIALES:
        repo_d.crear(
            Destino(
                id=None,
                codigo=d["codigo"],
                ciudad=d["ciudad"],
                zona=d["zona"],
                factor_costo=float(d["factor_costo"]),
            )
        )
    for item in PAQUETES_INICIALES:
        dest = repo_d.obtener_por_codigo(item["destino_codigo"])
        if dest is None or dest.id is None:
            continue
        categoria = clasificador.clasificar_por_peso(float(item["peso_kg"]))
        total = calculadora.cotizar(categoria, float(item["peso_kg"]), dest.factor_costo).total_cop
        repo_p.crear(
            Paquete(
                id=None,
                referencia=item["referencia"],
                peso_kg=float(item["peso_kg"]),
                destino_id=dest.id,
                categoria=categoria,
                costo_envio_cop=total,
                manifiesto_id=None,
                creado_en=None,
            )
        )


def _leer_linea(mensaje: str) -> str:
    return input(mensaje).strip()


def leer_int(mensaje: str, minimo: Optional[int] = None, maximo: Optional[int] = None) -> int:
    raw = _leer_linea(mensaje)
    try:
        valor = int(raw)
    except ValueError as exc:
        raise ValueError("Debe digitar un número entero válido.") from exc
    if minimo is not None and valor < minimo:
        raise ValueError(f"El valor debe ser mayor o igual a {minimo}.")
    if maximo is not None and valor > maximo:
        raise ValueError(f"El valor debe ser menor o igual a {maximo}.")
    return valor


def leer_float_positivo(mensaje: str) -> float:
    raw = _leer_linea(mensaje)
    try:
        valor = float(raw.replace(",", "."))
    except ValueError as exc:
        raise ValueError("Debe digitar un número decimal válido (use punto como separador).") from exc
    if valor < 0:
        raise ValueError("El valor no puede ser negativo.")
    return valor


def ejecutar_con_manejo(fn: Callable[[], None], ctx: str) -> None:
    try:
        fn()
    except ValueError as e:
        print(f"\n[!] Validación: {e}")
    except sqlite3.Error as e:
        print(f"\n[!] Base de datos: {e}")
    except Exception:
        print(f"\n[!] Error inesperado en {ctx}:")
        traceback.print_exc()


def submenu_destinos(conn: sqlite3.Connection) -> None:
    repo = RepositorioDestinos(conn)
    while True:
        print(
            """
--- DESTINOS ---
1) Listar
2) Crear
3) Actualizar
4) Eliminar
0) Volver
"""
        )
        try:
            op = leer_int("Opción: ", minimo=0, maximo=4)
        except ValueError as e:
            print(e)
            continue
        if op == 0:
            return
        if op == 1:
            items = repo.listar()
            if not items:
                print("(Sin destinos registrados.)")
            for d in items:
                print(
                    f"  [{d.id}] {d.codigo} | {d.ciudad} ({d.zona}) | factor={d.factor_costo:.3f}"
                )
        elif op == 2:

            def crear() -> None:
                codigo = _leer_linea("Código (ej. BOG-LOC): ")
                ciudad = _leer_linea("Ciudad: ")
                zona = _leer_linea("Zona (Local/Cundinamarca/Nacional/Especial): ")
                factor = leer_float_positivo("Factor de costo (>0, ej. 1.2): ")
                if factor <= 0:
                    raise ValueError("El factor debe ser > 0.")
                nuevo = Destino(id=None, codigo=codigo, ciudad=ciudad, zona=zona, factor_costo=factor)
                nuevo_id = repo.crear(nuevo)
                print(f"Destino creado con id={nuevo_id}.")

            ejecutar_con_manejo(crear, "crear destino")
        elif op == 3:

            def actualizar() -> None:
                did = leer_int("Id destino a actualizar: ", minimo=1)
                actual = repo.obtener_por_id(did)
                if actual is None:
                    raise ValueError("Destino no encontrado.")
                print(f"Editando: {actual.codigo} — deje en blanco para no cambiar.")
                codigo = _leer_linea(f"Código [{actual.codigo}]: ") or actual.codigo
                ciudad = _leer_linea(f"Ciudad [{actual.ciudad}]: ") or actual.ciudad
                zona = _leer_linea(f"Zona [{actual.zona}]: ") or actual.zona
                ftxt = _leer_linea(f"Factor [{actual.factor_costo}]: ")
                factor = float(ftxt.replace(",", ".")) if ftxt.strip() else actual.factor_costo
                if factor <= 0:
                    raise ValueError("El factor debe ser > 0.")
                repo.actualizar(did, Destino(id=did, codigo=codigo, ciudad=ciudad, zona=zona, factor_costo=factor))
                print("Destino actualizado.")

            ejecutar_con_manejo(actualizar, "actualizar destino")
        elif op == 4:

            def eliminar() -> None:
                did = leer_int("Id destino a eliminar: ", minimo=1)
                cur = conn.execute("SELECT COUNT(*) FROM paquetes WHERE destino_id = ?", (did,))
                n = int(cur.fetchone()[0])
                if n > 0:
                    raise ValueError(f"No se puede eliminar: hay {n} paquete(s) asociados.")
                if not repo.eliminar(did):
                    raise ValueError("Destino no encontrado.")
                print("Destino eliminado.")

            ejecutar_con_manejo(eliminar, "eliminar destino")


def submenu_paquetes(
    conn: sqlite3.Connection,
    clasificador: ClasificadorPaquetes,
    calculadora: CalculadoraCostoEnvio,
) -> None:
    repo_d = RepositorioDestinos(conn)
    repo_p = RepositorioPaquetes(conn)
    while True:
        print(
            """
--- PAQUETES ---
1) Listar
2) Registrar (peso + destino → clase + costo)
3) Actualizar
4) Eliminar
0) Volver
"""
        )
        try:
            op = leer_int("Opción: ", minimo=0, maximo=4)
        except ValueError as e:
            print(e)
            continue
        if op == 0:
            return
        if op == 1:
            for p in repo_p.listar():
                manifiesto_txt = str(p.manifiesto_id) if p.manifiesto_id is not None else "—"
                print(
                    f"  [{p.id}] {p.referencia} | {p.peso_kg:.2f} kg | {p.categoria} | "
                    f"${p.costo_envio_cop:,.2f} COP | destino_id={p.destino_id} | manifiesto={manifiesto_txt}"
                )
        elif op == 2:

            def crear() -> None:
                ref = _leer_linea("Referencia única del paquete: ")
                if not ref:
                    raise ValueError("La referencia es obligatoria.")
                peso = leer_float_positivo("Peso (kg): ")
                destinos = repo_d.listar()
                if not destinos:
                    raise ValueError("No hay destinos: cree al menos uno.")
                print("Destinos disponibles:")
                for d in destinos:
                    print(f"  [{d.id}] {d.codigo} — {d.ciudad} ({d.zona})")
                did = leer_int("Id destino: ", minimo=1)
                dest = repo_d.obtener_por_id(did)
                if dest is None or dest.id is None:
                    raise ValueError("Destino no encontrado.")
                categoria = clasificador.clasificar_por_peso(peso)
                total = calculadora.cotizar(categoria, peso, dest.factor_costo).total_cop
                pid = repo_p.crear(
                    Paquete(
                        id=None,
                        referencia=ref,
                        peso_kg=peso,
                        destino_id=dest.id,
                        categoria=categoria,
                        costo_envio_cop=total,
                        manifiesto_id=None,
                        creado_en=None,
                    )
                )
                print(
                    f"Paquete #{pid} guardado. Clasificación: {categoria}. "
                    f"Cotización estimada: ${total:,.2f} COP."
                )

            ejecutar_con_manejo(crear, "registrar paquete")
        elif op == 3:

            def actualizar() -> None:
                pid = leer_int("Id paquete: ", minimo=1)
                actual = repo_p.obtener(pid)
                if actual is None:
                    raise ValueError("Paquete no encontrado.")
                ref = _leer_linea(f"Referencia [{actual.referencia}]: ") or actual.referencia
                ptxt = _leer_linea(f"Peso kg [{actual.peso_kg}]: ")
                peso = float(ptxt.replace(",", ".")) if ptxt.strip() else actual.peso_kg
                if peso < 0:
                    raise ValueError("Peso inválido.")
                print("Destinos (id): ", ", ".join(str(d.id) for d in repo_d.listar()))
                did_txt = _leer_linea(f"destino_id [{actual.destino_id}]: ")
                did = int(did_txt) if did_txt.strip() else actual.destino_id
                dest = repo_d.obtener_por_id(did)
                if dest is None or dest.id is None:
                    raise ValueError("Destino no encontrado.")
                categoria = clasificador.clasificar_por_peso(peso)
                total = calculadora.cotizar(categoria, peso, dest.factor_costo).total_cop
                nuevo = Paquete(
                    id=actual.id,
                    referencia=ref,
                    peso_kg=peso,
                    destino_id=dest.id,
                    categoria=categoria,
                    costo_envio_cop=total,
                    manifiesto_id=actual.manifiesto_id,
                    creado_en=actual.creado_en,
                )
                repo_p.actualizar(pid, nuevo)
                print(f"Actualizado. Nueva clase: {categoria}. Nuevo costo: ${total:,.2f} COP.")

            ejecutar_con_manejo(actualizar, "actualizar paquete")
        elif op == 4:

            def eliminar() -> None:
                pid = leer_int("Id paquete a eliminar: ", minimo=1)
                if not repo_p.eliminar(pid):
                    raise ValueError("Paquete no encontrado.")
                print("Paquete eliminado.")

            ejecutar_con_manejo(eliminar, "eliminar paquete")


def submenu_manifiestos(conn: sqlite3.Connection) -> None:
    repo_m = RepositorioManifiestos(conn)
    repo_p = RepositorioPaquetes(conn)
    while True:
        print(
            """
--- MANIFIESTOS ---
1) Listar manifiestos
2) Crear manifiesto vacío
3) Armar manifiesto con paquetes PENDIENTES (orden por peso ascendente)
4) Ver / imprimir manifiesto (detalle ordenado)
5) Eliminar manifiesto (libera paquetes)
0) Volver
"""
        )
        try:
            op = leer_int("Opción: ", minimo=0, maximo=5)
        except ValueError as e:
            print(e)
            continue
        if op == 0:
            return
        if op == 1:
            for m in repo_m.listar():
                peso_t, costo_t, n = repo_m.totales_por_manifiesto(int(m.id) if m.id else 0)
                print(f"  [{m.id}] {m.codigo} — {m.titulo} | piezas={n} | peso={peso_t:.2f} kg | ${costo_t:,.2f}")
        elif op == 2:

            def crear() -> None:
                codigo = _leer_linea("Código manifiesto (único, ej. MF-20260506-01): ").upper()
                titulo = _leer_linea("Título / ruta (ej. Camión Zona Centro): ")
                mid = repo_m.crear(Manifiesto(id=None, codigo=codigo, titulo=titulo, creado_en=None))
                print(f"Manifiesto creado id={mid}.")

            ejecutar_con_manejo(crear, "crear manifiesto")
        elif op == 3:

            def armar() -> None:
                pendientes = repo_p.listar_sin_manifiesto()
                if not pendientes:
                    raise ValueError("No hay paquetes pendientes de manifiesto.")
                print("Paquetes pendientes (orden propuesto por peso):")
                ids_ordenados: List[int] = []
                for p in sorted(pendientes, key=lambda x: (x.peso_kg, x.id or 0)):
                    assert p.id is not None
                    ids_ordenados.append(p.id)
                    print(f"  {p.id} | {p.referencia} | {p.peso_kg:.2f} kg | {p.categoria}")
                mid = leer_int("Id manifiesto destino: ", minimo=1)
                if repo_m.obtener(mid) is None:
                    raise ValueError("Manifiesto no encontrado.")
                repo_p.asignar_manifiesto(ids_ordenados, mid)
                print(f"Se asignaron {len(ids_ordenados)} paquetes al manifiesto {mid}.")

            ejecutar_con_manejo(armar, "armar manifiesto")
        elif op == 4:

            def ver() -> None:
                mid = leer_int("Id manifiesto: ", minimo=1)
                cab = repo_m.obtener(mid)
                if cab is None:
                    raise ValueError("Manifiesto no encontrado.")
                lineas = repo_m.lineas_ordenadas_por_peso(mid)
                peso_t, costo_t, n = repo_m.totales_por_manifiesto(mid)
                print(f"\n=== MANIFIESTO {cab.codigo} ===")
                print(f"{cab.titulo} | registrado: {cab.creado_en}")
                print(f"Totales: {n} paquetes | {peso_t:.2f} kg | ${costo_t:,.2f} COP\n")
                for ln in lineas:
                    print(
                        f"  {ln.orden:02d}. [{ln.paquete_id}] {ln.referencia} | {ln.peso_kg:.2f} kg | "
                        f"{ln.categoria} → {ln.destino_codigo} ({ln.ciudad})"
                    )
                if not lineas:
                    print("  (Sin líneas aún.)")

            ejecutar_con_manejo(ver, "ver manifiesto")
        elif op == 5:

            def borrar() -> None:
                mid = leer_int("Id manifiesto a eliminar: ", minimo=1)
                if not repo_m.eliminar(mid):
                    raise ValueError("Manifiesto no encontrado.")
                print("Manifiesto eliminado y paquetes liberados.")

            ejecutar_con_manejo(borrar, "eliminar manifiesto")


def herramienta_cotizacion_rapida(conn: sqlite3.Connection) -> None:
    clasificador = ClasificadorPaquetes()
    calculadora = CalculadoraCostoEnvio()
    repo_d = RepositorioDestinos(conn)

    def run() -> None:
        peso = leer_float_positivo("Peso (kg) para cotizar: ")
        destinos = repo_d.listar()
        if not destinos:
            raise ValueError("No hay destinos.")
        for d in destinos:
            print(f"  [{d.id}] {d.codigo} — {d.ciudad} ({d.zona}), factor={d.factor_costo}")
        did = leer_int("Id destino: ", minimo=1)
        dest = repo_d.obtener_por_id(did)
        if dest is None:
            raise ValueError("Destino no encontrado.")
        cat = clasificador.clasificar_por_peso(peso)
        c = calculadora.cotizar(cat, peso, dest.factor_costo)
        print(f"\nClasificación sugerida: {cat}")
        print(f"Costo estimado: ${c.total_cop:,.2f} COP (base sin zona: ${c.subtotal_cop:,.2f})")

    ejecutar_con_manejo(run, "cotización rápida")


def menu_principal(conn: sqlite3.Connection) -> None:
    clasificador = ClasificadorPaquetes()
    calculadora = CalculadoraCostoEnvio()
    while True:
        print(
            f"""
========================================
 RUTA-ÓPTIMA | Clasificación y manifiestos
 Base de datos: {DB_PATH}
========================================
1) Destinos (CRUD)
2) Paquetes (CRUD + clasificación/costo)
3) Manifiestos (carga ordenada por peso)
4) Cotización rápida (sin guardar)
5) Mostrar ruta de la base y salida Power BI
0) Salir
"""
        )
        try:
            op = leer_int("Seleccione una opción: ", minimo=0, maximo=5)
        except ValueError as e:
            print(e)
            continue
        if op == 0:
            print("Hasta pronto.")
            return
        if op == 1:
            submenu_destinos(conn)
        elif op == 2:
            submenu_paquetes(conn, clasificador, calculadora)
        elif op == 3:
            submenu_manifiestos(conn)
        elif op == 4:
            herramienta_cotizacion_rapida(conn)
        elif op == 5:
            export_dir = os.path.join(BASE_DIR, "pbi_export")
            print(f"\nRuta absoluta .db:\n  {DB_PATH}")
            print("Para refrescar CSV de analítica ejecute:\n  python3 conectar_powerbi.py")
            print(f"Carpeta de exportación CSV: {export_dir}")


def main() -> None:
    conn = _conectar()
    try:
        inicializar_esquema(conn)
        repo_d = RepositorioDestinos(conn)
        repo_p = RepositorioPaquetes(conn)
        semillar_si_vacio(conn, repo_d, repo_p, ClasificadorPaquetes(), CalculadoraCostoEnvio())
        menu_principal(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario.")
        sys.exit(0)
