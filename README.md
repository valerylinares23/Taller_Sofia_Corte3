# Taller Sofia — Tercer Corte (Ruta-Óptima / Logística)

Proyecto **RETO 1: LOGÍSTICA — “Ruta-Óptima”**: clasificación de paquetes (Documento / Paquetería / Carga), cotización de envío, manifiestos ordenados por peso y exportación para analítica en Power BI.

## Estructura

- `ruta_optima/datos.py` — datos y reglas de negocio iniciales.
- `ruta_optima/destinos.py` — POO + repositorio SQLite de destinos.
- `ruta_optima/paquetes.py` — POO + clasificación por peso + repositorio.
- `ruta_optima/envios.py` — cálculo de costos por categoría y zona.
- `ruta_optima/manifiestos.py` — manifiestos y detalle ordenado por peso.
- `ruta_optima/main.py` — orquestador: crea `data/ruta_optima.db` con `os`, menú CRUD y validaciones.
- `ruta_optima/conectar_powerbi.py` — materializa CSV desde la misma BD para Power BI y deja metadatos de ruta.
- `ruta_optima/POWERBI_INSTRUCCIONES.txt` — pasos para armar el `.pbix` y al menos cuatro gráficas con filtros.

## Ejecución

```bash
cd ruta_optima
python3 main.py
```

Exportar datos para el tablero:

```bash
cd ruta_optima
python3 conectar_powerbi.py
```

## Entrega GitHub

- Incluya todos los `.py`, `data/ruta_optima.db`, los CSV en `pbi_export/` (opcional si se regeneran con el script) y el archivo **`RutaOptima.pbix`** creado en Power BI Desktop siguiendo `POWERBI_INSTRUCCIONES.txt`. El `.pbix` no se puede versionar de forma fiable desde este repositorio sin abrir Power BI Desktop al menos una vez.

## Reglas de clasificación (resumen)

- **Documento**: peso ≤ 0,5 kg.
- **Paquetería**: 0,5 kg < peso ≤ 30 kg.
- **Carga**: peso > 30 kg.

El costo combina tarifas por categoría y el **factor de costo** del destino configurado en `destinos`.
