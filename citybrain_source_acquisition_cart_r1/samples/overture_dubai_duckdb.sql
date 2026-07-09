-- CityBrain acquisition cart R1
-- Source: Overture Maps. Purpose: sample Dubai AOI places/buildings/roads with stable IDs.
-- Run from a machine with DuckDB >= 1.1, network access, and spatial/httpfs extensions.
-- NOTE: update release if a newer Overture release is desired.

INSTALL spatial;
INSTALL httpfs;
LOAD spatial;
LOAD httpfs;
SET s3_region='us-west-2';

-- Dubai rough bbox: min_lon=55.05, min_lat=24.85, max_lon=55.55, max_lat=25.35

COPY (
  SELECT
    id,
    names.primary AS name,
    categories.primary AS category,
    confidence,
    geometry
  FROM read_parquet(
    's3://overturemaps-us-west-2/release/2026-06-17.0/theme=places/type=place/*',
    filename=true,
    hive_partitioning=1
  )
  WHERE bbox.xmin BETWEEN 55.05 AND 55.55
    AND bbox.ymin BETWEEN 24.85 AND 25.35
  LIMIT 5000
) TO 'samples/overture_dubai_places_sample.geojson'
  WITH (FORMAT GDAL, DRIVER 'GeoJSON');

COPY (
  SELECT id, subtype, class, geometry
  FROM read_parquet(
    's3://overturemaps-us-west-2/release/2026-06-17.0/theme=transportation/type=segment/*',
    filename=true,
    hive_partitioning=1
  )
  WHERE bbox.xmin <= 55.55 AND bbox.xmax >= 55.05
    AND bbox.ymin <= 25.35 AND bbox.ymax >= 24.85
  LIMIT 5000
) TO 'samples/overture_dubai_roads_sample.geojson'
  WITH (FORMAT GDAL, DRIVER 'GeoJSON');
