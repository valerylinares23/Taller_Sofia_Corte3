"""Manifiestos de carga: agrupación de paquetes ordenados por peso."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass
class LineaManifiesto:
    orden: int
    paquete_id: int
    referencia: str
    peso_kg: float
    categoria: str
    destino_codigo: str
    ciudad: str


@dataclass
class Manifiesto:
    id: Optional[int]
    codigo: str
    titulo: str
    creado_en: Optional[str] = None

    def tupla_insert(self) -> Tuple[str, str, str]:
        return (
            self.codigo.strip().upper(),
            self.titulo.strip(),
            self.creado_en or datetime.now().isoformat(timespec="seconds"),
        )


class RepositorioManifiestos:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def crear(self, manifiesto: Manifiesto) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO manifiestos (codigo, titulo, creado_en)
            VALUES (?, ?, ?)
            """,
            manifiesto.tupla_insert(),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def listar(self) -> List[Manifiesto]:
        cur = self._conn.execute(
            "SELECT id, codigo, titulo, creado_en FROM manifiestos ORDER BY creado_en DESC"
        )
        return [Manifiesto(int(r[0]), r[1], r[2], r[3]) for r in cur.fetchall()]

    def obtener(self, manifiesto_id: int) -> Optional[Manifiesto]:
        cur = self._conn.execute(
            "SELECT id, codigo, titulo, creado_en FROM manifiestos WHERE id = ?", (manifiesto_id,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        return Manifiesto(int(row[0]), row[1], row[2], row[3])

    def eliminar(self, manifiesto_id: int) -> bool:
        self._conn.execute(
            "UPDATE paquetes SET manifiesto_id = NULL WHERE manifiesto_id = ?", (manifiesto_id,)
        )
        cur = self._conn.execute("DELETE FROM manifiestos WHERE id = ?", (manifiesto_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def lineas_ordenadas_por_peso(self, manifiesto_id: int) -> List[LineaManifiesto]:
        cur = self._conn.execute(
            """
            SELECT
                p.id,
                p.referencia,
                p.peso_kg,
                p.categoria,
                d.codigo,
                d.ciudad
            FROM paquetes p
            JOIN destinos d ON d.id = p.destino_id
            WHERE p.manifiesto_id = ?
            ORDER BY p.peso_kg ASC, p.id ASC
            """,
            (manifiesto_id,),
        )
        lineas: List[LineaManifiesto] = []
        for orden, row in enumerate(cur.fetchall(), start=1):
            lineas.append(
                LineaManifiesto(
                    orden=orden,
                    paquete_id=int(row[0]),
                    referencia=row[1],
                    peso_kg=float(row[2]),
                    categoria=row[3],
                    destino_codigo=row[4],
                    ciudad=row[5],
                )
            )
        return lineas

    def totales_por_manifiesto(self, manifiesto_id: int) -> Tuple[float, float, int]:
        cur = self._conn.execute(
            """
            SELECT COALESCE(SUM(peso_kg), 0), COALESCE(SUM(costo_envio_cop), 0), COUNT(*)
            FROM paquetes
            WHERE manifiesto_id = ?
            """,
            (manifiesto_id,),
        )
        peso, costo, n = cur.fetchone()
        return float(peso), float(costo), int(n)
