import geopandas as gpd
import pandas as pd
import boto3
import os
from shapely.geometry import Point
from dotenv import load_dotenv
import s3fs

# Load environment variables
load_dotenv()
os.environ['AWS_REGION'] = 'us-east-2'
os.environ['AWS_S3_ENDPOINT'] = 'https://s3.us-east-1.amazonaws.com'

# Download the ZIP file locally
s3 = boto3.client('s3')
bucket_name_raw = 'capstone-techcatalyst-raw-group-2'
zip_key = 'taxi_zones.zip'
local_zip_path = '/tmp/taxi_zones.zip'

s3.download_file(bucket_name_raw, zip_key, local_zip_path)

# Read the shapefile from the local ZIP
taxi_zones = gpd.read_file(f"zip://{local_zip_path}")

# Now continue with your existing logic
bucket_name = 'capstone-techcatalyst-transformed-group-2'
prefix = 'construction_cleaned/transformed'

response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.parquet')]

for file_key in files:
    print(file_key)
    s3_path = f's3://{bucket_name}/{file_key}'
    print(f"Processing {s3_path}")

    df = pd.read_parquet(s3_path)

    gs = gpd.GeoSeries.from_wkt(df['wkt'])
    gdf = gpd.GeoDataFrame(df, geometry=gs, crs="EPSG:2263")

    gdf = gdf.to_crs(taxi_zones.crs)
    print("Construction GeoDataFrame shape:", gdf.shape)
    print("Taxi Zones GeoDataFrame shape:", taxi_zones.shape)
    print("CRS match:", gdf.crs == taxi_zones.crs)
    print("Valid geometries:", gdf.geometry.is_valid.all())
    print("Empty geometries:", gdf.geometry.is_empty.sum())
    print("Bounds of construction data:", gdf.total_bounds)
    print("Bounds of taxi zones:", taxi_zones.total_bounds)


    joined = gpd.sjoin(gdf, taxi_zones, how='left', predicate='intersects')
    joined = joined.dropna()
    


    output_path = f's3://{bucket_name}/construction_cleaned/joined/joined_{os.path.basename(file_key)}'
    joined.to_parquet(output_path)
