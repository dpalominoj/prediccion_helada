// Funciones para la interfaz de predicción de heladas

async function realizarPrediccionHoy() {
  console.log("Solicitando pronóstico automático con Open-Meteo...");
  const statusBox = document.getElementById('statusBox');
  const statusText = document.getElementById('statusText');
  // const statusImage = document.getElementById('statusImage'); // No se usa activamente para cambiar imagen por ahora
  const resultadoGlobalDiv = document.getElementById('resultadoGlobalPronostico');
  const tablaPronosticosDiv = document.getElementById('tablaPronosticosDetallados');

  // Limpiar resultados anteriores
  resultadoGlobalDiv.innerHTML = 'Calculando pronóstico...';
  tablaPronosticosDiv.innerHTML = '';
  statusText.textContent = 'Procesando...';
  statusBox.className = 'flex-1 rounded-md flex flex-col items-center justify-center py-8 px-6 bg-blue-500'; // Color de carga


  try {
    // Ya no se envían datos manuales para esta función, se llama al endpoint de pronóstico automático
    const response = await fetch('/pronostico_automatico', { // Llamada al nuevo endpoint
      method: 'GET', // O POST si se necesitan parámetros
      headers: {
        'Content-Type': 'application/json', // Aunque no hay body para GET, es buena práctica
      },
    });

    const responseBody = await response.json();

    if (!response.ok) {
      const errorMessage = responseBody.error || `Error del servidor: ${response.status}`;
      console.error("Error en la respuesta del servidor (pronóstico automático):", response.status, responseBody);
      throw new Error(errorMessage);
    }

    console.log("Pronóstico automático recibido:", responseBody);

    // responseBody es el objeto de la predicción única guardada
    const prediccion = responseBody;

    resultadoGlobalDiv.innerHTML = `<strong>${prediccion.mensaje || "Predicción procesada."}</strong>`;

    // Actualizar los campos de la interfaz con la nueva predicción
    document.getElementById('ubicacion').textContent = prediccion.ubicacion || "N/A";
    document.getElementById('estacion').textContent = prediccion.estacion_meteorologica || "N/A";

    if (prediccion.fecha_prediccion_para) {
      const fechaPredPara = new Date(prediccion.fecha_prediccion_para);
      document.getElementById('fecha').textContent = fechaPredPara.toLocaleDateString('es-ES', {
        day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'
      });
    } else {
      document.getElementById('fecha').textContent = "N/A";
    }

    document.getElementById('intensidad').textContent = prediccion.intensidad || 'N/A';
    document.getElementById('duracion').textContent = prediccion.duracion_estimada_horas ? `${prediccion.duracion_estimada_horas} horas` : 'N/A';

    statusText.textContent = prediccion.resultado ? prediccion.resultado.replace(/_/g, ' ') : 'No Determinado';
    statusBox.className = 'flex-1 rounded-md flex flex-col items-center justify-center py-8 px-6'; // Reset clases

    if (prediccion.resultado === 'Probable') {
      statusBox.classList.add('bg-red-500');
    } else if (prediccion.resultado === 'Poco Probable') {
      statusBox.classList.add('bg-green-500');
    } else {
      statusBox.classList.add('bg-yellow-500'); // Para "No Determinada" u otros casos
    }

    // Limpiar la tabla de pronósticos detallados ya que solo tenemos una predicción principal ahora.
    // Si en el futuro /pronostico_automatico devolviera múltiples, esta parte se podría reintroducir.
    tablaPronosticosDiv.innerHTML = '';

    // No hay una propiedad 'errores' directamente en la respuesta exitosa de /pronostico_automatico
    // Los errores se manejan a través del bloque catch o el !response.ok
    // Si hubiera errores parciales devueltos en un caso de éxito, necesitaríamos ajustar la API y este código.

  } catch (error) {
    console.error("Error al realizar el pronóstico automático (catch en JS):", error);
    resultadoGlobalDiv.textContent = `Error: ${error.message}`;
    statusText.textContent = 'Error';
    statusBox.className = 'flex-1 rounded-md flex flex-col items-center justify-center py-8 px-6 bg-gray-500';
    document.getElementById('ubicacion').textContent = '-';
    document.getElementById('estacion').textContent = '-';
    document.getElementById('fecha').textContent = '-';
    document.getElementById('intensidad').textContent = 'Error';
    document.getElementById('duracion').textContent = 'Error';
  }
}

function verRegistroPredicciones() {
  console.log("Redirigiendo a la página de registros...");
  window.location.href = '/registros_ui';
}

// Opcional: Cargar una predicción inicial o estado al cargar la página
window.onload = async () => {
  console.log("Página cargada. Intentando cargar predicción actual.");
  const statusBox = document.getElementById('statusBox');
  const statusText = document.getElementById('statusText');
  const ubicacionEl = document.getElementById('ubicacion');
  const estacionEl = document.getElementById('estacion');
  const fechaEl = document.getElementById('fecha');
  const intensidadEl = document.getElementById('intensidad');
  const duracionEl = document.getElementById('duracion');
  // const statusImage = document.getElementById('statusImage'); // No se usa para cambiar imagen dinámicamente por ahora

  try {
    const response = await fetch('/obtener_prediccion_actual');
    const data = await response.json();

    if (response.ok) {
      console.log("Predicción actual recibida:", data);
      statusText.textContent = data.resultado ? data.resultado.replace(/_/g, ' ') : 'No Determinado';
      ubicacionEl.textContent = data.ubicacion || 'N/A';
      estacionEl.textContent = data.estacion_meteorologica || 'N/A';

      if (data.fecha_prediccion_para) {
        const fechaPred = new Date(data.fecha_prediccion_para);
        fechaEl.textContent = fechaPred.toLocaleDateString('es-ES', {
          day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'
        });
      } else {
        fechaEl.textContent = 'N/A';
      }

      intensidadEl.textContent = data.intensidad || 'N/A';
      duracionEl.textContent = data.duracion_estimada_horas ? `${data.duracion_estimada_horas} horas` : 'N/A';

      statusBox.className = 'flex-1 rounded-md flex flex-col items-center justify-center py-8 px-6'; // Reset clases
      if (data.resultado === 'Probable') {
        statusBox.classList.add('bg-red-500');
      } else if (data.resultado === 'Poco Probable') {
        statusBox.classList.add('bg-green-500');
      } else {
        statusBox.classList.add('bg-yellow-500'); // Neutral para "No Determinada" o si no hay resultado
      }
    } else {
      console.log("No hay predicción actual disponible o error:", data.mensaje || response.status);
      statusText.textContent = 'Listo para predicción';
      statusBox.className = 'flex-1 rounded-md flex flex-col items-center justify-center py-8 px-6 bg-gray-400';
      ubicacionEl.textContent = 'N/A';
      estacionEl.textContent = 'N/A';
      fechaEl.textContent = 'N/A';
      intensidadEl.textContent = 'N/A';
      duracionEl.textContent = 'N/A';
    }
  } catch (error) {
    console.error("Error al cargar la predicción actual (catch en JS):", error);
    statusText.textContent = 'Error al cargar';
    statusBox.className = 'flex-1 rounded-md flex flex-col items-center justify-center py-8 px-6 bg-gray-500';
    ubicacionEl.textContent = 'Error';
    estacionEl.textContent = 'Error';
    fechaEl.textContent = 'Error';
    intensidadEl.textContent = 'Error';
    duracionEl.textContent = 'Error';
  }
};
