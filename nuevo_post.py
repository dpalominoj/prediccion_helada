import pandas as pd
import joblib
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import matplotlib.pyplot as plt

# 1. Cargar datos desde un archivo CSV
# El CSV debe contener las columnas:
# 'Temperatura', 'Humedad Relativa', 'Presión Atmosférica',
# 'Radiación Solar', 'Humedad del Suelo', 'Temperatura del Suelo', 'Helada'
# donde 'Helada' es la variable objetivo con valores 0 o 1.

df = pd.read_csv('./Data_set/nuevo_dato.csv')

# 2. Definir características (X) y variable objetivo (y)
X = df[['Temperatura', 'HumedadRelativa', 'PresionAtmosferica',
         'HumedadSuelo']]
y = df['HeladaSuelo']

# 3. Dividir en conjuntos de entrenamiento y prueba (80% train, 20% test)
# Stratify asegura distribución similar de clases en ambos conjuntos
test_size = 0.2
random_state = 42
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=test_size, random_state=random_state, stratify=y
)

# 4. Crear el modelo de árbol de decisión
# Ajusta hiperparámetros como max_depth o min_samples_split según necesidades
model = DecisionTreeClassifier(random_state=random_state, max_depth=None)

# 5. Entrenar el modelo
model.fit(X_train, y_train)

# 6. Guardar el modelo en local para uso futuro
modelo_path = 'sin_radiacion_temsuelo.pkl'
joblib.dump(model, modelo_path)
print(f"Modelo guardado en: {modelo_path}")

# 7. Visualizar el árbol de decisión entrenado
plt.figure(figsize=(20, 10))
plot_tree(
    model,
    feature_names=X.columns,
    class_names=[str(c) for c in model.classes_],
    filled=True,
    rounded=True,
    fontsize=12
)
plt.title("Árbol de Decisión - Helada Suelo")
plt.show()

# 8. Realizar predicciones
y_pred = model.predict(X_test)

# 9. Evaluar el rendimiento
metrics = {
    'Métrica': ['Exactitud', 'Precisión', 'Sensibilidad', 'F1-score'],
    'Valor': [
        accuracy_score(y_test, y_pred),
        precision_score(y_test, y_pred),
        recall_score(y_test, y_pred),
        f1_score(y_test, y_pred)
    ]
}

df_metrics = pd.DataFrame(metrics)

# 10. Imprimir métricas de manera ordenada y profesional
print('\n--- Resultados de Evaluación del Modelo ---')
print(df_metrics.to_string(index=False, float_format='{:,.2f}'.format))

# Opcional: exportar métricas a CSV para inclusión en tesis
metrics_csv = 'metricas_evaluacion.csv'
df_metrics.to_csv(metrics_csv, index=False)
print(f"Métricas exportadas a: {metrics_csv}")
