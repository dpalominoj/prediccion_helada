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

    resultadoGlobalDiv.innerHTML = `<strong>${responseBody.mensaje}</strong>`;

    if (responseBody.predicciones_exitosas && responseBody.predicciones_exitosas.length > 0) {
      // Actualizar el cuadro de estado principal con la primera predicción significativa
      // (o un resumen general si es más apropiado)
      // Por ahora, tomamos la primera predicción como referencia para el estado general.
      const primeraPred Significativa = responseBody.predicciones_exitosas.find(p => p.resultado === "Probable") || responseBody.predicciones_exitosas[0];

      if (primeraPred Significativa) {
        document.getElementById('ubicacion').textContent = "Patala, Pucará (Open-Meteo)"; // Actualizar con datos relevantes
        document.getElementById('estacion').textContent = "Open-Meteo Forecast";

        const fechaPredPara = new Date(primeraPred Significativa.fecha_prediccion_para);
        document.getElementById('fecha').textContent = `Desde ${fechaPredPara.toLocaleDateString('es-ES', { day: 'numeric', month: 'long' })} ${fechaPredPara.toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit'})} (Múltiples horarios)`;

        document.getElementById('intensidad').textContent = primeraPred Significativa.intensidad || 'Varía';
        document.getElementById('duracion').textContent = 'Varía por hora'; // Duración es horaria

        statusText.textContent = primeraPred Significativa.resultado ? primeraPred Significativa.resultado.replace(/_/g, ' ') : 'No Determinado';
        statusBox.className = 'flex-1 rounded-md flex flex-col items-center justify-center py-8 px-6'; // Reset clases
        if (primeraPred Significativa.resultado === 'Probable') {
          statusBox.classList.add('bg-red-500');
        } else if (primeraPred Significativa.resultado === 'Poco Probable') {
          statusBox.classList.add('bg-green-500');
        } else {
          statusBox.classList.add('bg-yellow-500');
        }
      } else {
         statusText.textContent = "No hay predicciones significativas.";
         statusBox.className = 'flex-1 rounded-md flex flex-col items-center justify-center py-8 px-6 bg-gray-500';
      }

      // Opcional: Mostrar una tabla con todas las predicciones horarias
      let tablaHTML = '<table class="w-full text-xs text-gray-700 mt-2"><thead><tr class="bg-gray-100"><th class="px-2 py-1">Fecha/Hora</th><th class="px-2 py-1">Resultado</th><th class="px-2 py-1">Intensidad</th></tr></thead><tbody>';
      responseBody.predicciones_exitosas.forEach(pred => {
        const fechaHora = new Date(pred.fecha_prediccion_para);
        tablaHTML += `<tr class="border-b border-gray-200">
                        <td class="px-2 py-1">${fechaHora.toLocaleString('es-ES')}</td>
                        <td class="px-2 py-1">${pred.resultado || '-'}</td>
                        <td class="px-2 py-1">${pred.intensidad || '-'}</td>
                      </tr>`;
      });
      tablaHTML += '</tbody></table>';
      tablaPronosticosDiv.innerHTML = tablaHTML;

    } else {
      statusText.textContent = "No se generaron predicciones.";
      statusBox.className = 'flex-1 rounded-md flex flex-col items-center justify-center py-8 px-6 bg-gray-500';
      document.getElementById('ubicacion').textContent = '-';
      document.getElementById('estacion').textContent = '-';
      document.getElementById('fecha').textContent = '-';
      document.getElementById('intensidad').textContent = '-';
      document.getElementById('duracion').textContent = '-';
    }

    if (responseBody.errores && responseBody.errores.length > 0) {
        resultadoGlobalDiv.innerHTML += `<br><span style="color: red;">Se encontraron ${responseBody.errores.length} errores durante el proceso. Ver consola para detalles.</span>`;
        responseBody.errores.forEach(err => console.error("Error en predicción horaria:", err));
    }

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
window.onload = () => {
  console.log("Página cargada. Interfaz de predicción lista.");
  // Limpiar el estado inicial si es el placeholder
  if (document.getElementById('statusText').textContent === 'helada probable') {
    document.getElementById('statusText').textContent = 'Listo para predicción';
    document.getElementById('statusBox').className = 'flex-1 rounded-md flex flex-col items-center justify-center py-8 px-6 bg-gray-400'; // Un color neutral
    document.getElementById('ubicacion').textContent = 'N/A';
    document.getElementById('estacion').textContent = 'N/A';
    document.getElementById('fecha').textContent = 'N/A';
    document.getElementById('intensidad').textContent = 'N/A';
    document.getElementById('duracion').textContent = 'N/A';
  }
};
