"""
Datos iniciales y reglas de negocio para Ruta-Óptima (logística Bogotá).
"""

from __future__ import annotations

# Clasificación por peso (kg): Documento | Paquetería | Carga
PESO_MAX_DOCUMENTO_KG = 0.5
PESO_MAX_PAQUETERIA_KG = 30.0

# Tarifas base en COP (ajustables por zona con factor_destino)
TARIFA_DOCUMENTO_BASE = 8_000.0
TARIFA_DOCUMENTO_POR_KG = 4_000.0

TARIFA_PAQUETERIA_BASE = 15_000.0
TARIFA_PAQUETERIA_POR_KG = 2_500.0

TARIFA_CARGA_BASE = 45_000.0
TARIFA_CARGA_POR_KG = 1_800.0

CATEGORIAS_VALIDAS = ("Documento", "Paquetería", "Carga")

# Semillas: destinos frecuentes desde centro de clasificación en Bogotá
DESTINOS_INICIALES = [
    {
        "codigo": "BOG-LOC",
        "ciudad": "Bogotá D.C.",
        "zona": "Local",
        "factor_costo": 1.0,
    },
    {
        "codigo": "CUND-NORTE",
        "ciudad": "Chía",
        "zona": "Cundinamarca",
        "factor_costo": 1.12,
    },
    {
        "codigo": "MED",
        "ciudad": "Medellín",
        "zona": "Nacional",
        "factor_costo": 1.28,
    },
    {
        "codigo": "CTG",
        "ciudad": "Cartagena",
        "zona": "Nacional",
        "factor_costo": 1.32,
    },
    {
        "codigo": "LET",
        "ciudad": "Leticia",
        "zona": "Especial",
        "factor_costo": 1.55,
    },
]

PAQUETES_INICIALES = [
    # peso_kg, destino_codigo (opcional para poblar tras crear destinos)
    {"referencia": "INIT-DOC-001", "peso_kg": 0.25, "destino_codigo": "BOG-LOC"},
    {"referencia": "INIT-PQ-002", "peso_kg": 5.5, "destino_codigo": "MED"},
    {"referencia": "INIT-PQ-003", "peso_kg": 18.0, "destino_codigo": "CTG"},
    {"referencia": "INIT-CG-004", "peso_kg": 42.0, "destino_codigo": "LET"},
]
