import pandas as pd
import matplotlib.pyplot as plt
import joblib  # o usa pickle si lo guardaste así

# 1. Cargar el modelo guardado
modelo = joblib.load('./Hipoetesis/sin_radiacion_temsuelo.pkl')  # cambia esto por la ruta de tu archivo

# 2. Cargar el CSV
df = pd.read_csv('./Data_set/test.csv')  # cambia por la ruta de tu archivo CSV

# Definir X e y
X = df[['Temperatura', 'HumedadRelativa', 'PresionAtmosferica', 'HumedadSuelo']]  # Asegúrate de que los nombres coincidan

# 4. Obtener importancias
importancias = modelo.feature_importances_
nombres = X.columns

# 5. Crear DataFrame ordenado
df_importancias = pd.DataFrame({
    'Variable': nombres,
    'Importancia': importancias
}).sort_values(by='Importancia', ascending=False)

print(df_importancias)

# 6. Graficar
plt.figure(figsize=(10, 6))
plt.barh(df_importancias['Variable'], df_importancias['Importancia'], color='forestgreen')
plt.xlabel('Importancia')
plt.title('Importancia de Variables en el Modelo de Árbol de Decisión')
plt.gca().invert_yaxis()
plt.grid(True, axis='x', linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()
