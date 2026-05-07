"""Cálculo de costos de envío según categoría, peso y zona."""

from __future__ import annotations

from dataclasses import dataclass

from datos import (
    TARIFA_CARGA_BASE,
    TARIFA_CARGA_POR_KG,
    TARIFA_DOCUMENTO_BASE,
    TARIFA_DOCUMENTO_POR_KG,
    TARIFA_PAQUETERIA_BASE,
    TARIFA_PAQUETERIA_POR_KG,
)


@dataclass
class Cotizacion:
    categoria: str
    peso_kg: float
    factor_zona: float
    subtotal_cop: float
    total_cop: float


class CalculadoraCostoEnvio:
    """Aplica tarifas por categoría y multiplica por factor de destino."""

    def cotizar(self, categoria: str, peso_kg: float, factor_destino: float) -> Cotizacion:
        if peso_kg < 0:
            raise ValueError("El peso no puede ser negativo.")
        if factor_destino <= 0:
            raise ValueError("El factor de destino debe ser positivo.")

        categoria = categoria.strip()
        if categoria == "Documento":
            base = TARIFA_DOCUMENTO_BASE + TARIFA_DOCUMENTO_POR_KG * peso_kg
        elif categoria == "Paquetería":
            base = TARIFA_PAQUETERIA_BASE + TARIFA_PAQUETERIA_POR_KG * peso_kg
        elif categoria == "Carga":
            base = TARIFA_CARGA_BASE + TARIFA_CARGA_POR_KG * peso_kg
        else:
            raise ValueError("Categoría desconocida para cotización.")

        total = round(base * float(factor_destino), 2)
        return Cotizacion(
            categoria=categoria,
            peso_kg=float(peso_kg),
            factor_zona=float(factor_destino),
            subtotal_cop=round(base, 2),
            total_cop=total,
        )
