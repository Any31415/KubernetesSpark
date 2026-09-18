from pyspark.sql import SparkSession
from pyspark.ml.clustering import KMeansModel

spark = SparkSession.builder \
    .appName("OpenFoodFactsInference") \
    .master("local[*]") \
    .config("spark.jars", "mysql-connector-j.jar") \
    .getOrCreate()

# Выгрузка данных из источника
jdbc_url = "jdbc:mysql://localhost:3306/off_clustering"
products_df = spark.read.jdbc(
    url=jdbc_url,
    table="products",
    properties={"user": "lab6user", "password": "lab2", "driver": "com.mysql.cj.jdbc.Driver"}
)

# Подготовка признаков
from pyspark.ml.feature import VectorAssembler, StandardScaler

feature_cols = [
    "energy_kcal_100g", "fat_100g", "saturated_fat_100g",
    "carbohydrates_100g", "sugars_100g", "proteins_100g",
    "salt_100g", "fiber_100g"
]
assembler = VectorAssembler(inputCols=feature_cols, outputCol="features_raw")
df_vec = assembler.transform(products_df)

scaler = StandardScaler(inputCol="features_raw", outputCol="features", withStd=True, withMean=True)
df_scaled = scaler.fit(df_vec).transform(df_vec)

# Загружаем уже обученную модель из лабы 5
model = KMeansModel.load("kmeans_model")

# Инференс -предсказываем кластер для каждого продукта
predictions = model.transform(df_scaled).withColumnRenamed("id", "product_id").select("product_id", "cluster")

# Отправка результата обратно в БД
predictions.write.jdbc(
    url=jdbc_url,
    table="cluster_results",
    mode="append",
    properties={"user": "lab6user", "password": "lab2", "driver": "com.mysql.cj.jdbc.Driver"}
)

print(f"Обработано и записано: {predictions.count()} предсказаний")
spark.stop()