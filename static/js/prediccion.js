// Funciones para la interfaz de predicción de heladas

async function realizarPrediccionHoy() {
  console.log("Solicitando predicción para hoy...");
  const statusBox = document.getElementById('statusBox');
  const statusText = document.getElementById('statusText');
  const statusImage = document.getElementById('statusImage'); // Asegúrate que la imagen exista o maneja su ausencia

  // Mostrar estado de carga
  statusText.textContent = 'Calculando predicción...';
  statusBox.classList.remove('bg-green-500', 'bg-red-500', 'bg-yellow-500', 'bg-gray-500');
  statusBox.classList.add('bg-blue-500'); // Color de carga

  try {
    // Datos de ejemplo para enviar al backend.
    // ESTOS DEBEN COINCIDIR CON `COLUMNAS_FEATURES_PREDICCION` en app.py
    // ['Temperatura', 'HumedadRelativa', 'PresionAtmosferica', 'HumedadSuelo']
    const datosParaPredecir = {
      // Valores de ejemplo para las features que el modelo espera:
      "Temperatura": 5.0,       // Grados Celsius
      "HumedadRelativa": 85.0,  // Porcentaje
      "PresionAtmosferica": 1012.0, // hPa
      "HumedadSuelo": 60.0,      // Porcentaje

      // Información adicional que se puede usar para la BD pero no por el modelo directamente:
      "ubicacion": "Valle Central (Ejemplo JS)",
      "estacion": "Estación Meteorológica Principal (Ejemplo JS)"
    };
    // En una implementación real, estos datos podrían venir de inputs en el HTML,
    // sensores, o una API meteorológica externa.

    console.log("Enviando datos para predicción:", datosParaPredecir);

    const response = await fetch('/predecir', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(datosParaPredecir),
    });

    const responseBody = await response.json(); // Leer el cuerpo de la respuesta una vez

    if (!response.ok) {
      // Usar el mensaje de error del backend si está disponible
      const errorMessage = responseBody.error || `Error del servidor: ${response.status}`;
      console.error("Error en la respuesta del servidor:", response.status, responseBody);
      throw new Error(errorMessage);
    }

    const data = responseBody; // Usar el cuerpo ya leído
    console.log("Predicción recibida del backend:", data);

    // Actualizar la interfaz con los datos recibidos
    document.getElementById('ubicacion').textContent = data.ubicacion || 'No especificada';
    document.getElementById('estacion').textContent = data.estacion_meteorologica || 'No especificada';

    const fechaPredPara = new Date(data.fecha_prediccion_para);
    document.getElementById('fecha').textContent = fechaPredPara.toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' }) + " (UTC)";

    document.getElementById('intensidad').textContent = data.intensidad || 'No determinada';
    document.getElementById('duracion').textContent = data.duracion_estimada_horas !== null ? `${data.duracion_estimada_horas.toFixed(1)} horas` : 'No determinada';

    // Actualizar el cuadro de estado principal
    let textoResultado = data.resultado ? data.resultado.replace(/_/g, ' ') : 'No Determinado';
    if (data.mensaje_adicional) { // Añadir mensaje del modelo si existe
        // textoResultado += ` (${data.mensaje_adicional})`;
        // El mensaje_adicional ya incluye "HELADA" o "NO HELADA", así que podría ser redundante
        // o podríamos mostrar solo data.mensaje_adicional en statusText
        statusText.textContent = data.mensaje_adicional; // Mostrar el mensaje del modelo
    } else {
        statusText.textContent = textoResultado;
    }


    statusBox.classList.remove('bg-blue-500');
    if (data.resultado === 'Probable') {
      statusBox.classList.add('bg-red-500');
      // statusImage.src = 'url_icono_helada_probable.png';
    } else if (data.resultado === 'Poco Probable') {
      statusBox.classList.add('bg-green-500');
      // statusImage.src = 'url_icono_helada_no_probable.png';
    } else { // No Determinada u otro estado
      statusBox.classList.add('bg-yellow-500');
      // statusImage.src = 'url_icono_default.png';
    }

  } catch (error) {
    console.error("Error al realizar la predicción (catch en JS):", error);
    statusText.textContent = `Error: ${error.message}`;
    document.getElementById('ubicacion').textContent = '-';
    document.getElementById('estacion').textContent = '-';
    document.getElementById('fecha').textContent = '-';
    document.getElementById('intensidad').textContent = 'Error';
    document.getElementById('duracion').textContent = 'Error';
    statusBox.classList.remove('bg-blue-500');
    statusBox.classList.add('bg-gray-500'); // Color de error
  }
}

function verRegistroPredicciones() {
  console.log("Redirigiendo a la página de registros...");
  window.location.href = '/registros_ui';
}

// Opcional: Cargar una predicción inicial o estado al cargar la página
window.onload = () => {
  console.log("Página cargada. Interfaz de predicción lista.");
  // Se podría llamar a una función que obtenga la última predicción si es necesario
  // Por ejemplo:
  // if (document.getElementById('statusText').textContent === 'helada probable') { // Si es el texto inicial
  //   // realizarPrediccionHoy(); // O una función que cargue la última predicción sin "re-predecir"
  // }
};
