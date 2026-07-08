/**
 * TicketsManager - Gestión de escaneo OCR de tickets
 * Patrón: Manager singleton
 * Responsabilidad: Procesar y confirmar tickets
 */
class TicketsManager {
  constructor(apiClient, domManager) {
    this.api = apiClient;
    this.dom = domManager;

    this.ticketActual = null;
    this.listeners = new Set();
  }

  // ===== PROCESAMIENTO OCR =====
  async procesarArchivo(file) {
    try {
      const formData = new FormData();
      formData.append('foto', file);

      const resultado = await this.api.procesarTicket(formData);
      this.ticketActual = resultado;
      this.notificar('ticket-procesado', resultado);
      return resultado;
    } catch (error) {
      console.error('Error procesando ticket:', error);
      this.notificar('ticket-error', error.message);
      throw error;
    }
  }

  // ===== CONFIRMACIÓN DE ITEMS =====
  async confirmarItems(items) {
    try {
      const resultado = await this.api.confirmarTicket({ items });
      this.notificar('ticket-confirmado', resultado);
      this.ticketActual = null;
      return resultado;
    } catch (error) {
      console.error('Error confirmando ticket:', error);
      this.notificar('ticket-error', error.message);
      throw error;
    }
  }

  // ===== LIMPIAR ESTADO =====
  limpiar() {
    this.ticketActual = null;
    this.notificar('ticket-cancelado', null);
  }

  // ===== HELPERS =====
  get ticketProcesado() {
    return this.ticketActual !== null;
  }

  get itemsTicket() {
    return this.ticketActual?.productos || [];
  }

  // ===== EVENT EMITTER =====
  suscribir(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notificar(evento, datos) {
    this.listeners.forEach(listener => {
      try {
        listener(evento, datos);
      } catch (error) {
        console.error(`Error en listener para ${evento}:`, error);
      }
    });
  }
}

// Crear instancia global
window.ticketsManager = new TicketsManager(window.API, window.DOM);
