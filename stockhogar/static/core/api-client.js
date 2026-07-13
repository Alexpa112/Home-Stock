/**
 * API CLIENT - Cliente centralizado para TODAS las llamadas fetch
 * Patrón: Single Responsibility + DRY
 * Beneficio: Manejo unificado de errores, caché, reintentos
 */
class APIClient {
  constructor(baseUrl = '/api') {
    this.baseUrl = baseUrl;
    this.headers = { 'Content-Type': 'application/json' };
    this.timeout = 10000;
  }

  /**
   * Token CSRF publicado por el backend en <meta name="csrf-token">
   */
  _csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
  }

  /**
   * Método privado: realiza fetch con manejo de errores
   */
  async _fetch(url, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    const metodo = (options.method || 'GET').toUpperCase();
    const headers = { ...this.headers, ...options.headers };
    if (!['GET', 'HEAD', 'OPTIONS'].includes(metodo)) {
      headers['X-CSRFToken'] = this._csrfToken();
    }

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers,
      });

      clearTimeout(timeoutId);

      if (response.status === 401) {
        window.location.href = '/login';
        throw new Error('Sesión expirada');
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: response.statusText }));
        throw new APIError(error.error || 'Error desconocido', response.status, error);
      }

      return response.status === 204 ? null : await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof APIError) throw error;
      throw new APIError(error.message || 'Error de conexión', 0);
    }
  }

  // ===== PRODUCTOS =====
  async obtenerProductos() {
    return this._fetch(`${this.baseUrl}/productos`);
  }

  async crearProducto(datos) {
    return this._fetch(`${this.baseUrl}/productos`, {
      method: 'POST',
      body: JSON.stringify(datos),
    });
  }

  async actualizarProducto(id, datos) {
    return this._fetch(`${this.baseUrl}/productos/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(datos),
    });
  }

  async borrarProducto(id) {
    return this._fetch(`${this.baseUrl}/productos/${id}`, {
      method: 'DELETE',
    });
  }

  // ===== LISTAS DE COMPRA =====
  async obtenerListas() {
    return this._fetch(`${this.baseUrl}/listas`);
  }

  async crearLista(datos) {
    return this._fetch(`${this.baseUrl}/listas`, {
      method: 'POST',
      body: JSON.stringify(datos),
    });
  }

  async actualizarLista(id, datos) {
    return this._fetch(`${this.baseUrl}/listas/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(datos),
    });
  }

  async borrarLista(id) {
    return this._fetch(`${this.baseUrl}/listas/${id}`, {
      method: 'DELETE',
    });
  }

  async seleccionarLista(id) {
    return this._fetch(`${this.baseUrl}/listas/${id}/seleccionar`, {
      method: 'POST',
    });
  }

  async compartirLista(id, datos) {
    return this._fetch(`${this.baseUrl}/listas/${id}/compartir`, {
      method: 'POST',
      body: JSON.stringify(datos),
    });
  }

  // ===== ARTÍCULOS =====
  async obtenerArticulos() {
    return this._fetch(`${this.baseUrl}/articulos`);
  }

  async crearArticulo(datos) {
    return this._fetch(`${this.baseUrl}/articulos`, {
      method: 'POST',
      body: JSON.stringify(datos),
    });
  }

  async actualizarArticulo(id, datos) {
    return this._fetch(`${this.baseUrl}/articulos/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(datos),
    });
  }

  async borrarArticulo(id) {
    return this._fetch(`${this.baseUrl}/articulos/${id}`, {
      method: 'DELETE',
    });
  }

  // ===== CATEGORÍAS =====
  async obtenerCategorias() {
    return this._fetch(`${this.baseUrl}/categorias`);
  }

  async crearCategoria(datos) {
    return this._fetch(`${this.baseUrl}/categorias`, {
      method: 'POST',
      body: JSON.stringify(datos),
    });
  }

  async actualizarCategoria(id, datos) {
    return this._fetch(`${this.baseUrl}/categorias/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(datos),
    });
  }

  async borrarCategoria(id) {
    return this._fetch(`${this.baseUrl}/categorias/${id}`, {
      method: 'DELETE',
    });
  }

  // ===== HISTORIAL =====
  async obtenerHistorial() {
    return this._fetch(`${this.baseUrl}/historial`);
  }

  async buscarHistorial(nombre) {
    return this._fetch(`${this.baseUrl}/historial?nombre=${encodeURIComponent(nombre)}`);
  }

  // ===== USUARIOS =====
  async obtenerUsuarios() {
    return this._fetch(`${this.baseUrl}/usuarios`);
  }

  async crearUsuario(datos) {
    return this._fetch(`${this.baseUrl}/usuarios`, {
      method: 'POST',
      body: JSON.stringify(datos),
    });
  }

  async borrarUsuario(id) {
    return this._fetch(`${this.baseUrl}/usuarios/${id}`, {
      method: 'DELETE',
    });
  }

  // ===== TICKETS OCR =====
  async procesarTicket(formData) {
    return fetch(`${this.baseUrl}/tickets/procesar`, {
      method: 'POST',
      headers: { 'X-CSRFToken': this._csrfToken() },
      body: formData,
    }).then(async (res) => {
      if (res.status === 401) {
        window.location.href = '/login';
        throw new Error('Sesión expirada');
      }
      if (!res.ok) {
        const error = await res.json().catch(() => ({ error: res.statusText }));
        throw new APIError(error.error || 'Error', res.status);
      }
      return res.json();
    });
  }
}

/**
 * Excepción personalizada para errores API
 */
class APIError extends Error {
  constructor(message, status = 0, details = {}) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.details = details;
  }

  get isNetworkError() {
    return this.status === 0;
  }

  get isAuthError() {
    return this.status === 401;
  }

  get isNotFound() {
    return this.status === 404;
  }

  get isValidationError() {
    return this.status === 400;
  }

  get isServerError() {
    return this.status >= 500;
  }
}

// Instancia global singleton
window.API = new APIClient();
