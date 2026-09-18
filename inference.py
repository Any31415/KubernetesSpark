from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeansModel
import urllib.request
import json

spark = SparkSession.builder \
    .appName("OpenFoodFactsInference") \
    .master("local[*]") \
    .getOrCreate()

DATAMART_URL = "http://localhost:8080"

# 1. Выгрузка данных через витрину (не напрямую из MySQL!)
print("Выгрузка данных из витрины...")
with urllib.request.urlopen(f"{DATAMART_URL}/data") as response:
    data = json.loads(response.read().decode("utf-8"))
print(f"Получено записей: {len(data)}")

# 2. Превращаем JSON в Spark DataFrame
products_df = spark.createDataFrame(data)

# 3. Подготовка признаков
feature_cols = [
    "energy_kcal_100g", "fat_100g", "saturated_fat_100g",
    "carbohydrates_100g", "sugars_100g", "proteins_100g",
    "salt_100g", "fiber_100g"
]
assembler = VectorAssembler(inputCols=feature_cols, outputCol="features_raw")
df_vec = assembler.transform(products_df)

scaler = StandardScaler(inputCol="features_raw", outputCol="features", withStd=True, withMean=True)
df_scaled = scaler.fit(df_vec).transform(df_vec)

# 4. Загружаем уже обученную модель из лабы 5
print("Загрузка обученной модели...")
model = KMeansModel.load("kmeans_model")

# 5. Инференс
predictions = model.transform(df_scaled).select("id", "cluster")
results = [{"product_id": row["id"], "cluster": row["cluster"]} for row in predictions.collect()]

# 6. Отправка результата обратно через витрину
print("Отправка предсказаний в витрину...")
payload = json.dumps(results, separators=(",", ":")).encode("utf-8")
req = urllib.request.Request(f"{DATAMART_URL}/results", data=payload, headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req) as response:
    result = json.loads(response.read().decode("utf-8"))

print(f"Готово. {result}")
spark.stop()