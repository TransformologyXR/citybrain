"""
CityBrain acquisition cart R1: Copernicus CDS ERA5 sample.
Requires ~/.cdsapirc or env CDSAPI_URL/CDSAPI_KEY configured by the operator.
"""
import cdsapi

client = cdsapi.Client()
client.retrieve(
    "reanalysis-era5-single-levels",
    {
        "product_type": "reanalysis",
        "variable": ["2m_temperature", "total_precipitation", "10m_u_component_of_wind", "10m_v_component_of_wind"],
        "year": "2026",
        "month": "07",
        "day": ["01"],
        "time": ["00:00", "06:00", "12:00", "18:00"],
        # North, West, South, East around Dubai. Keep tiny for smoke.
        "area": [25.35, 55.05, 24.85, 55.55],
        "format": "netcdf",
    },
    "samples/era5_dubai_2026-07-01_smoke.nc",
)
