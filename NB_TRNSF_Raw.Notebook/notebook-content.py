# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "32226d85-cead-4b4f-ae2e-8bad46422ffd",
# META       "default_lakehouse_name": "LH_STORE_RAW",
# META       "default_lakehouse_workspace_id": "6025657f-f096-4f69-85a1-06b1f352098c",
# META       "known_lakehouses": [
# META         {
# META           "id": "32226d85-cead-4b4f-ae2e-8bad46422ffd"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

import os
from pyspark.sql import functions as F

# Incremental tables
csv_files = ["customer.csv", "sales.csv", "product.csv", "store.csv"]

# Schema name
schema_name = "raw"

# Create schema if it doesn't exist
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")


for csv_file in csv_files:

    table_name = os.path.splitext(csv_file)[0]

    # Read the source table
    df = spark.read.format("csv").option("header","true").load(f"Files/raw/{csv_file}")

    # remove column name invalid chars

    df = df.select([F.col(col).alias(col.replace(' ', '')) for col in df.columns])
   
    # Write to the target schema, replacing the existing table

    df.write.mode("overwrite").option("overwriteSchema", "true").format("delta").saveAsTable(f"raw.{table_name}")    
    

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
