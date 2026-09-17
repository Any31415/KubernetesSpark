from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator
import matplotlib.pyplot as plt

spark = SparkSession.builder \
    .appName("OpenFoodFactsClustering") \
    .master("local[*]") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()

# Загрузка данных
df = spark.read.csv("data.csv.gz", header=True, inferSchema=True, sep="\t")
print(f"Всего строк в исходном датасете: {df.count()}")

# Отбираем числовые колонки
feature_cols = [
    "energy-kcal_100g", "fat_100g", "saturated-fat_100g",
    "carbohydrates_100g", "sugars_100g", "proteins_100g",
    "salt_100g", "fiber_100g"
]
df_clean = df.select(feature_cols).na.drop()
print(f"Строк после удаления пропусков: {df_clean.count()}")

# Выборка адекватного размера
sample_fraction = min(1.0, 100000 / df_clean.count())
df_sample = df_clean.sample(withReplacement=False, fraction=sample_fraction, seed=42)
df_sample.cache()
print(f"Размер выборки для обучения: {df_sample.count()}")

# Сборка признаков + масштабирование
assembler = VectorAssembler(inputCols=feature_cols, outputCol="features_raw")
df_vec = assembler.transform(df_sample)

scaler = StandardScaler(inputCol="features_raw", outputCol="features", withStd=True, withMean=True)
df_scaled = scaler.fit(df_vec).transform(df_vec)
df_scaled.cache()

# Elbow method
print("\n--- Подбор k методом локтя ---")
costs = []
for k in range(2, 9):
    km = KMeans(featuresCol="features", predictionCol="cluster", k=k, seed=42)
    m = km.fit(df_scaled)
    cost = m.summary.trainingCost
    costs.append(cost)
    print(f"k={k}: WSSSE={cost:.2f}")

# график
ks = list(range(2, 9))
plt.figure(figsize=(8, 5))
plt.plot(ks, costs, marker='o')
plt.xlabel("Число кластеров (k)")
plt.ylabel("WSSSE (сумма квадратов расстояний)")
plt.title("Метод локтя для подбора k")
plt.grid(True)
plt.savefig("elbow_plot.png")
print("График сохранён в elbow_plot.png")

# ищем k, где падение между соседними точками
# замедляется сильнее всего (макс второй производной)
diffs = [costs[i] - costs[i+1] for i in range(len(costs)-1)]
diff_of_diffs = [diffs[i] - diffs[i+1] for i in range(len(diffs)-1)]
best_k_index = diff_of_diffs.index(max(diff_of_diffs)) + 1  # +1 т.к. diffs короче costs на 1
optimal_k = ks[best_k_index]
print(f"\nАвтоматически выбранное k (по локтю): {optimal_k}")

# Финальное обучение с оптимальным k
kmeans = KMeans(featuresCol="features", predictionCol="cluster", k=optimal_k, seed=42)
model = kmeans.fit(df_scaled)
predictions = model.transform(df_scaled)

# Метрика качества
evaluator = ClusteringEvaluator(featuresCol="features", predictionCol="cluster")
silhouette = evaluator.evaluate(predictions)
print(f"\nSilhouette score (k={optimal_k}): {silhouette}")

# Размеры кластеров
predictions.groupBy("cluster").count().orderBy("cluster").show()

# Сохраняем модель
model.write().overwrite().save("kmeans_model")

spark.stop()