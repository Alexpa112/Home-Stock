/**
 * USUARIOS MANAGER - Gestión de usuarios
 * Patrón: Manager OOP + Event Emitter
 * Responsabilidad: CRUD usuarios, autenticación
 */

class UsuariosManager {
  constructor(api, dom) {
    this.api = api;
    this.dom = dom;

    this.usuarios = [];
    this.usuarioActual = null;

    // Event emitter
    this.listeners = new Set();

    // DOM elements
    this.usuariosListaEl = this.dom.get('usuariosLista');
    this.usuarioCampoNombre = this.dom.get('usuarioCampoNombre');
    this.usuarioCampoPassword = this.dom.get('usuarioCampoPassword');
    this.btnAnadirUsuario = this.dom.get('btnAnadirUsuario');
    this.usuariosEstado = this.dom.get('usuariosEstado');

    this._setupEventListeners();
    this.cargar();
  }

  // ===== EVENT EMITTER =====
  suscribir(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notificar(evento, datos = null) {
    this.listeners.forEach(listener => {
      try {
        listener(evento, datos);
      } catch (error) {
        console.error(`Error en listener para ${evento}:`, error);
      }
    });
  }

  // ===== SETUP =====
  _setupEventListeners() {
    if (this.btnAnadirUsuario) {
      this.btnAnadirUsuario.addEventListener('click', () => this._crearUsuario());
    }
  }

  // ===== CRUD =====
  async cargar() {
    try {
      this.usuarios = await this.api.obtenerUsuarios();
      this.render();
      this.notificar('usuarios-cargados', this.usuarios);
    } catch (error) {
      console.error('Error cargando usuarios:', error);
      this.usuarios = [];
      this.render();
    }
  }

  async crear(datos) {
    try {
      const res = await fetch('/api/auth/registrar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(datos)
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || 'Error creando usuario');
      }

      const nuevoUsuario = await res.json();
      this.usuarios.push(nuevoUsuario);
      this.render();
      this.notificar('usuario-creado', nuevoUsuario);
      return nuevoUsuario;
    } catch (error) {
      console.error('Error creando usuario:', error);
      throw error;
    }
  }

  async borrar(id) {
    try {
      const res = await fetch(`/api/usuarios/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.error || 'Error borrando usuario');
      }

      this.usuarios = this.usuarios.filter(u => u.id !== id);
      this.render();
      this.notificar('usuario-borrado', id);
    } catch (error) {
      console.error('Error borrando usuario:', error);
      throw error;
    }
  }

  // ===== RENDERIZADO =====
  render() {
    if (!this.usuariosListaEl) return;

    this.usuariosListaEl.innerHTML = '';

    if (!Array.isArray(this.usuarios) || this.usuarios.length === 0) {
      this.usuariosListaEl.innerHTML = '<div style="padding: 20px; color: var(--text-soft);">Sin usuarios</div>';
      return;
    }

    this.usuarios.forEach(usuario => {
      const chip = this._crearElementoUsuario(usuario);
      this.usuariosListaEl.appendChild(chip);
    });
  }

  _crearElementoUsuario(usuario) {
    const chip = document.createElement('div');
    chip.className = 'categoria-chip';
    chip.innerHTML = `<span>👤 ${this._escapeHtml(usuario.nombre_usuario)}</span>`;

    // Solo mostrar borrar si hay más de 1 usuario
    if (this.usuarios.length > 1) {
      const btnBorrar = document.createElement('button');
      btnBorrar.type = 'button';
      btnBorrar.title = 'Borrar usuario';
      btnBorrar.textContent = '✕';
      btnBorrar.addEventListener('click', async () => {
        if (confirm(`¿Borrar usuario "${usuario.nombre_usuario}"?`)) {
          try {
            await this.borrar(usuario.id);
          } catch (error) {
            alert(error.message);
          }
        }
      });
      chip.appendChild(btnBorrar);
    }

    return chip;
  }

  // ===== HANDLERS PRIVADOS =====
  async _crearUsuario() {
    const nombre = this.usuarioCampoNombre?.value.trim();
    const password = this.usuarioCampoPassword?.value;

    if (!nombre || !password || password.length < 4) {
      if (this.usuariosEstado) {
        this.usuariosEstado.textContent = 'Nombre y contraseña (mín. 4 caracteres)';
        this.usuariosEstado.hidden = false;
      }
      return;
    }

    try {
      await this.crear({ usuario: nombre, password });
      if (this.usuarioCampoNombre) this.usuarioCampoNombre.value = '';
      if (this.usuarioCampoPassword) this.usuarioCampoPassword.value = '';
      if (this.usuariosEstado) this.usuariosEstado.hidden = true;
      alert('Usuario creado');
    } catch (error) {
      if (this.usuariosEstado) {
        this.usuariosEstado.textContent = error.message;
        this.usuariosEstado.hidden = false;
      }
    }
  }

  _escapeHtml(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
  }
}

// Instanciar cuando esté listo
document.addEventListener('DOMContentLoaded', () => {
  if (window.API && window.DOM) {
    window.usuariosManager = new UsuariosManager(window.API, window.DOM);
  }
});
