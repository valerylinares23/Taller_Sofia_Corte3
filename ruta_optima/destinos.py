"""Modelo y persistencia de destinos de envío."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


@dataclass
class Destino:
    id: Optional[int]
    codigo: str
    ciudad: str
    zona: str
    factor_costo: float

    def tupla_db(self) -> Tuple[str, str, str, float]:
        return (self.codigo.strip().upper(), self.ciudad.strip(), self.zona.strip(), float(self.factor_costo))


class RepositorioDestinos:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def crear(self, destino: Destino) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO destinos (codigo, ciudad, zona, factor_costo)
            VALUES (?, ?, ?, ?)
            """,
            destino.tupla_db(),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def listar(self) -> List[Destino]:
        cur = self._conn.execute(
            "SELECT id, codigo, ciudad, zona, factor_costo FROM destinos ORDER BY codigo"
        )
        return [Destino(int(r[0]), r[1], r[2], r[3], float(r[4])) for r in cur.fetchall()]

    def obtener_por_id(self, destino_id: int) -> Optional[Destino]:
        cur = self._conn.execute(
            "SELECT id, codigo, ciudad, zona, factor_costo FROM destinos WHERE id = ?",
            (destino_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return Destino(int(row[0]), row[1], row[2], row[3], float(row[4]))

    def obtener_por_codigo(self, codigo: str) -> Optional[Destino]:
        cur = self._conn.execute(
            "SELECT id, codigo, ciudad, zona, factor_costo FROM destinos WHERE codigo = ?",
            (codigo.strip().upper(),),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return Destino(int(row[0]), row[1], row[2], row[3], float(row[4]))

    def actualizar(self, destino_id: int, destino: Destino) -> bool:
        cur = self._conn.execute(
            """
            UPDATE destinos SET codigo = ?, ciudad = ?, zona = ?, factor_costo = ?
            WHERE id = ?
            """,
            (*destino.tupla_db(), destino_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def eliminar(self, destino_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM destinos WHERE id = ?", (destino_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def codigos_existentes(self) -> Sequence[str]:
        cur = self._conn.execute("SELECT codigo FROM destinos")
        return [r[0] for r in cur.fetchall()]
