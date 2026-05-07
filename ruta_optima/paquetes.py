"""Paquetes: clasificación por peso y persistencia."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from datos import (
    CATEGORIAS_VALIDAS,
    PESO_MAX_DOCUMENTO_KG,
    PESO_MAX_PAQUETERIA_KG,
)


@dataclass
class Paquete:
    id: Optional[int]
    referencia: str
    peso_kg: float
    destino_id: int
    categoria: str
    costo_envio_cop: float
    manifiesto_id: Optional[int]
    creado_en: Optional[str] = None

    def tupla_insert(self) -> Tuple:
        return (
            self.referencia.strip(),
            float(self.peso_kg),
            int(self.destino_id),
            self.categoria,
            float(self.costo_envio_cop),
            self.manifiesto_id,
            self.creado_en or datetime.now().isoformat(timespec="seconds"),
        )


class ClasificadorPaquetes:
    @staticmethod
    def clasificar_por_peso(peso_kg: float) -> str:
        if peso_kg < 0:
            raise ValueError("El peso no puede ser negativo.")
        if peso_kg <= PESO_MAX_DOCUMENTO_KG:
            return "Documento"
        if peso_kg <= PESO_MAX_PAQUETERIA_KG:
            return "Paquetería"
        return "Carga"

    @staticmethod
    def validar_categoria(categoria: str) -> str:
        c = categoria.strip()
        if c not in CATEGORIAS_VALIDAS:
            raise ValueError(f"Categoría inválida. Use una de: {', '.join(CATEGORIAS_VALIDAS)}")
        return c


class RepositorioPaquetes:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def crear(self, paquete: Paquete) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO paquetes (referencia, peso_kg, destino_id, categoria, costo_envio_cop, manifiesto_id, creado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            paquete.tupla_insert(),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def listar(self) -> List[Paquete]:
        cur = self._conn.execute(
            """
            SELECT id, referencia, peso_kg, destino_id, categoria, costo_envio_cop, manifiesto_id, creado_en
            FROM paquetes
            ORDER BY creado_en DESC, id DESC
            """
        )
        return [self._row_to_paquete(r) for r in cur.fetchall()]

    def listar_sin_manifiesto(self) -> List[Paquete]:
        cur = self._conn.execute(
            """
            SELECT id, referencia, peso_kg, destino_id, categoria, costo_envio_cop, manifiesto_id, creado_en
            FROM paquetes
            WHERE manifiesto_id IS NULL
            ORDER BY peso_kg ASC, id ASC
            """
        )
        return [self._row_to_paquete(r) for r in cur.fetchall()]

    def obtener(self, paquete_id: int) -> Optional[Paquete]:
        cur = self._conn.execute(
            """
            SELECT id, referencia, peso_kg, destino_id, categoria, costo_envio_cop, manifiesto_id, creado_en
            FROM paquetes WHERE id = ?
            """,
            (paquete_id,),
        )
        row = cur.fetchone()
        return self._row_to_paquete(row) if row else None

    def actualizar(self, paquete_id: int, paquete: Paquete) -> bool:
        cur = self._conn.execute(
            """
            UPDATE paquetes
            SET referencia = ?, peso_kg = ?, destino_id = ?, categoria = ?, costo_envio_cop = ?,
                manifiesto_id = ?
            WHERE id = ?
            """,
            (
                paquete.referencia.strip(),
                float(paquete.peso_kg),
                int(paquete.destino_id),
                paquete.categoria,
                float(paquete.costo_envio_cop),
                paquete.manifiesto_id,
                paquete_id,
            ),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def eliminar(self, paquete_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM paquetes WHERE id = ?", (paquete_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def asignar_manifiesto(self, paquete_ids: List[int], manifiesto_id: int) -> None:
        placeholders = ",".join("?" * len(paquete_ids))
        self._conn.execute(
            f"UPDATE paquetes SET manifiesto_id = ? WHERE id IN ({placeholders})",
            [manifiesto_id, *paquete_ids],
        )
        self._conn.commit()

    @staticmethod
    def _row_to_paquete(row) -> Paquete:
        return Paquete(
            int(row[0]),
            row[1],
            float(row[2]),
            int(row[3]),
            row[4],
            float(row[5]),
            int(row[6]) if row[6] is not None else None,
            row[7],
        )
