import json
import requests
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

# Step 1: Download low-resolution world GeoJSON (Natural Earth 1:110m)
world_url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
world_response = requests.get(world_url)
world_data = world_response.json()

# Step 2: Download complete India GeoJSON (including disputed areas)
india_url = "https://raw.githubusercontent.com/datameet/maps/master/Country/india-composite.geojson"
india_response = requests.get(india_url)
india_data = india_response.json()

# Load into GeoPandas for manipulation
world_gdf = gpd.GeoDataFrame.from_features(world_data['features'])
india_gdf = gpd.GeoDataFrame.from_features(india_data['features'])

# Set CRS to EPSG:4326 (WGS84) as these GeoJSONs use lat/long coordinates
world_gdf.crs = "EPSG:4326"
india_gdf.crs = "EPSG:4326"

# Dissolve India to a single geometry if multi-feature
if len(india_gdf) > 1:
    india_geometry = unary_union(india_gdf.geometry)
    india_gdf = gpd.GeoDataFrame([{'geometry': india_geometry, 'NAME': 'India', 'ISO_A3': 'IND'}], crs=world_gdf.crs)
else:
    india_gdf = india_gdf[['geometry']].copy()
    india_gdf['NAME'] = 'India'
    india_gdf['ISO_A3'] = 'IND'
    india_gdf.crs = "EPSG:4326"  # Re-set after copy

# Step 3: Remove existing India from world
world_gdf = world_gdf[world_gdf['ISO_A3'] != 'IND']

# Step 4: Adjust neighboring countries for overlaps (e.g., subtract disputed areas from Pakistan and China)
neighbors = ['PAK', 'CHN']  # Add more if needed

for iso in neighbors:
    neighbor_idx = world_gdf[world_gdf['ISO_A3'] == iso].index
    if not neighbor_idx.empty:
        neighbor_geom = world_gdf.loc[neighbor_idx[0], 'geometry']
        overlap = neighbor_geom.intersection(india_gdf.geometry.iloc[0])
        if not overlap.is_empty:
            new_geom = neighbor_geom.difference(overlap)
            world_gdf.loc[neighbor_idx[0], 'geometry'] = new_geom

# Step 5: Add the complete India to the world GeoDataFrame
world_gdf = gpd.pd.concat([world_gdf, india_gdf], ignore_index=True)

# Step 6: Convert back to GeoJSON
world_gdf = world_gdf.to_crs("EPSG:4326")

# Create FeatureCollection with minimal properties
features = []
for _, row in world_gdf.iterrows():
    feature = {
        "type": "Feature",
        "properties": {
            "NAME": row.get('NAME', ''),
            "ISO_A3": row.get('ISO_A3', '')
        },
        "geometry": row['geometry'].__geo_interface__
    }
    features.append(feature)

geojson = {
    "type": "FeatureCollection",
    "features": features
}

# Save to file with moderate indentation for readability (file size ~2-5 MB)
with open("world_with_complete_india_lowres.geojson", "w") as f:
    json.dump(geojson, f, indent=2)

print("GeoJSON file saved as 'world_with_complete_india_lowres.geojson'")