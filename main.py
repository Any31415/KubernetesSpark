from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("WordCountTest").master("local[*]").getOrCreate()
text = spark.sparkContext.parallelize(["hello spark hello world", "spark works fine"])
counts = text.flatMap(lambda line: line.split(" ")) \
    .map(lambda word: (word, 1)) \
    .reduceByKey(lambda a, b: a + b)
print(counts.collect())
spark.stop()