import pandas as pd
import joblib
from sklearn.metrics import precision_score, recall_score, f1_score

# ---------------------------------------------------
# Código para evaluación según la hipótesis H₀₂:
# H₀₂: Evaluar el desempeño en precisión, recall y F1
#       del modelo de árbol de decisión ya entrenado.
# ---------------------------------------------------

# 1. Cargar modelo entrenado
modelo_path = './Hipoetesis/sin_radiacion_temsuelo.pkl'
model = joblib.load(modelo_path)
print(f"Modelo cargado desde: {modelo_path}")

# 2. Cargar datos de prueba (asegúrate de usar el mismo preprocesamiento que en entrenamiento)
#    El CSV debe contener las mismas columnas de características usadas en entrenamiento.
df_test = pd.read_csv('./Data_set/test2.csv')  # Ruta a tu CSV de test

# 3. Definir X_test y y_test
X_test = df_test[['Temperatura', 'HumedadRelativa', 'PresionAtmosferica', 'HumedadSuelo']]
y_test = df_test['HeladaSuelo']

# 4. Realizar predicciones sobre el conjunto de prueba
y_pred = model.predict(X_test)

# 5. Calcular métricas de desempeño
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)

# 6. Mostrar resultados
print("\n--- Evaluación según H₀₂: Desempeño del modelo ---")
print(f"Precisión: {precision:.2f}")
print(f"Recall (Sensibilidad): {recall:.2f}")
print(f"F1-score: {f1:.2f}")

# 7. Exportar métricas si se desea
df_metrics = pd.DataFrame({
    'Métrica': ['Precisión', 'Recall', 'F1-score'],
    'Valor': [precision, recall, f1]
})
metrics_csv = 'metricas_H02.csv'
df_metrics.to_csv(metrics_csv, index=False)
print(f"Métricas H₀₂ exportadas a: {metrics_csv}")
