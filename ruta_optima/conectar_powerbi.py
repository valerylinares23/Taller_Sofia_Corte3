"""
Conexión de analítica (Power BI) a la base SQLite del proyecto.

Qué hace este script (enlaza Python → datos → Power BI):
1) Garantiza que exista la base `data/ruta_optima.db` (crea esquema si falta).
2) Exporta tablas y vistas de analítica a CSV en `pbi_export/` para importación en Power BI.
3) Deja un archivo de metadatos con la ruta absoluta del .db (útil al configurar ODBC o rutas).

Flujo recomendado en Power BI Desktop:
- Obtener datos → Texto/CSV (o carpeta) y apuntar a los archivos en `pbi_export/`.
- Opcional avanzado: instalador del controlador ODBC para SQLite y conexión directa al .db.

Gráficas sugeridas (mínimo 4, con filtros cruzados):
- Barras: costo_total_cop por categoría (dataset `v_resumen_categoria.csv`).
- Barras/cluster: cantidad_paquetes por zona (`v_resumen_zona.csv`).
- Líneas: tendencia de costos por día (`v_paquetes_analitica.csv`, eje fecha_dia).
- Tarjetas + tabla: totales por manifiesto (`v_manifiesto_resumen.csv`).
"""

from __future__ import annotations

import csv
import os
import sqlite3
from typing import Iterable, List, Sequence, Tuple

from main import DB_PATH, _conectar, inicializar_esquema


EXPORT_SPECS: Sequence[Tuple[str, str]] = (
    ("destinos", "SELECT * FROM destinos"),
    ("paquetes", "SELECT * FROM paquetes"),
    ("manifiestos", "SELECT * FROM manifiestos"),
    ("v_paquetes_analitica", "SELECT * FROM v_paquetes_analitica"),
    ("v_resumen_categoria", "SELECT * FROM v_resumen_categoria"),
    ("v_resumen_zona", "SELECT * FROM v_resumen_zona"),
    ("v_manifiesto_resumen", "SELECT * FROM v_manifiesto_resumen"),
)


def _export_query(cursor: sqlite3.Cursor, query: str) -> Tuple[List[str], List[sqlite3.Row]]:
    cursor.execute(query)
    rows = cursor.fetchall()
    names = [d[0] for d in cursor.description] if cursor.description else []
    return names, rows


def exportar_csv(conn: sqlite3.Connection, carpeta: str) -> List[str]:
    os.makedirs(carpeta, exist_ok=True)
    escritas: List[str] = []
    cur = conn.cursor()
    cur.row_factory = sqlite3.Row
    for nombre, sql in EXPORT_SPECS:
        colnames, data = _export_query(cur, sql)
        ruta = os.path.join(carpeta, f"{nombre}.csv")
        with open(ruta, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(colnames)
            for row in data:
                writer.writerow([row[c] for c in colnames])
        escritas.append(ruta)
    return escritas


def escribir_meta(carpeta: str, archivos: Iterable[str]) -> str:
    meta = os.path.join(carpeta, "powerbi_connection_meta.txt")
    with open(meta, "w", encoding="utf-8") as fh:
        fh.write("Ruta absoluta de la base SQLite (fuente principal del sistema):\n")
        fh.write(os.path.abspath(DB_PATH) + "\n\n")
        fh.write("Archivos CSV generados para importación en Power BI:\n")
        for a in archivos:
            fh.write(a + "\n")
    return meta


def main() -> None:
    conn = _conectar()
    try:
        inicializar_esquema(conn)
        carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pbi_export")
        archivos = exportar_csv(conn, carpeta)
        meta = escribir_meta(carpeta, archivos)
        print("Exportación lista.")
        print(f"Metadatos: {meta}")
        print(f"Base de datos: {os.path.abspath(DB_PATH)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
