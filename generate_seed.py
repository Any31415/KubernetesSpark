from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("SeedExport").master("local[*]").getOrCreate()

df = spark.read.csv("data.csv.gz", header=True, inferSchema=True, sep="\t")

feature_cols = [
    "energy-kcal_100g", "fat_100g", "saturated-fat_100g",
    "carbohydrates_100g", "sugars_100g", "proteins_100g",
    "salt_100g", "fiber_100g"
]
df_clean = df.select(feature_cols).na.drop()
df_sample = df_clean.sample(withReplacement=False, fraction=min(1.0, 100000 / df_clean.count()), seed=42)

pdf = df_sample.toPandas()
print(f"Строк для выгрузки: {len(pdf)}")

cols = "energy_kcal_100g, fat_100g, saturated_fat_100g, carbohydrates_100g, sugars_100g, proteins_100g, salt_100g, fiber_100g"

with open("init/02-data.sql", "w") as f:
    batch_size = 1000
    for i in range(0, len(pdf), batch_size):
        batch = pdf.iloc[i:i+batch_size]
        values = ",\n".join(
            "(" + ",".join(str(v) for v in row) + ")" for row in batch.values
        )
        f.write(f"INSERT INTO products ({cols}) VALUES\n{values};\n")

print("Готово: init/02-data.sql")
spark.stop()