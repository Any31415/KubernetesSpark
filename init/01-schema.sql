CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    energy_kcal_100g FLOAT,
    fat_100g FLOAT,
    saturated_fat_100g FLOAT,
    carbohydrates_100g FLOAT,
    sugars_100g FLOAT,
    proteins_100g FLOAT,
    salt_100g FLOAT,
    fiber_100g FLOAT
);

CREATE TABLE cluster_results (
    product_id INT,
    cluster INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);