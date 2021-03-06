from pyspark.sql import SparkSession, Row
from pyspark.sql.functions import col,sequence
from pyspark.sql import SQLContext
from pyspark.sql.types import StructType
from pyspark.sql.functions import monotonically_increasing_id
import numpy as np
import pandas as pd
import math
import os
import itertools
from tabulate import tabulate
from loguru import logger
from pathlib import Path
import matplotlib.pyplot as plt

def init_spark():

    # "spark.driver.memory" must not exceed the total memory of the device: SWAP + RAM

    spark = SparkSession.builder \
        .appName("LoadParquets") \
        .config("spark.executor.memory","6g") \
        .config("spark.driver.memory", "70g") \
        .config("spark.driver.maxResultSize",0) \
        .getOrCreate()

    sc = spark.sparkContext
    return spark,sc

# init Spark
spark,sc = init_spark()

# open the dataframe from parquet files
project_folder = "projects/delta_benchmark/" 
project_paths = [project_folder+name for name in os.listdir(project_folder) if os.path.isdir(os.path.join(project_folder, name))]

# limit
#project_paths = ['projects/delta_benchmark/p8_results']
logger.info(F"All project folders: {project_paths}")

bench_params = { # target_delay
    'p8_results':0.8,
    'p9_results':0.9,
    'p99_results':0.99,
    'p999_results':0.999,
}

results = pd.DataFrame(columns=["delay target","delta","no-aqm"])
for folder_name in bench_params.keys():
    project_path = [s for s in project_paths if folder_name in s]
    project_path = project_path[0]
    #print(project_path)

    logger.info(F"Starting importing parquet files in: {project_path}")

    records_path = project_path + '/records/'
    all_files = os.listdir(records_path)
    files = []
    for f in all_files:
        if f.endswith(".parquet"):
            files.append(records_path + f)

    # limit
    #files = [files[0]]

    df=spark.read.parquet(*files)

    total_tasks = df.count()
    logger.info(f"Number of imported samples: {total_tasks}")
    dropped_tasks = df.where(df.end_time == -1).count()
    logger.info(f"Number of dropped tasks: {dropped_tasks}")
    delayed_tasks = df.where(df.end2end_delay > df.delay_bound).count()
    logger.info(f"Number of delayed tasks: {delayed_tasks}")

    results.loc[len(results)] = [ str(bench_params[folder_name]), (dropped_tasks+delayed_tasks)/total_tasks, 1.00-bench_params[folder_name] ]

ax = results.plot(x="delay target", y=["delta","no-aqm"], kind="bar")
ax.set_yscale('log')
ax.set_yticks(1.00 - np.array(list(bench_params.values())))
ax.set_xlabel('Target delay')
ax.set_ylabel('Failed tasks ratio')
# draw the legend
ax.legend()
ax.grid()
plt.tight_layout()
plt.savefig('result.png')


exit(0)
bars = [ str(par) for par in bench_params.values()]


y_pos = np.arange(len(bars))
fig, ax = plt.subplots()
ax.bar(
    y_pos,
    results,
    label='delta',
)
ax.bar(
    y_pos,
    1.00-np.array(list(bench_params.values())),
    label='no-aqm',
)
# fix x axis
#ax.set_xticks(range(math.ceil(minx),math.floor(maxx),100))
plt.xticks(y_pos, bars)
plt.yticks(y_pos, list(bench_params.values()))
ax.set_yscale('log')
ax.set_xlabel('Target delay')
ax.set_ylabel('Failed tasks ratio')

# draw the legend
ax.legend()
ax.grid()

fig.savefig('result.png')
    
