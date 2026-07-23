/**
 * Tests para FormBuilder
 * Cubre: generación de formulario, inyección en modal, validación
 */
const FormBuilder = require('./form-builder.js');

describe('FormBuilder', () => {
  beforeEach(() => {
    global.Toast = { error: jest.fn() };
  });

  describe('crearFormularioLista()', () => {
    test('devuelve un <form> con el id esperado', () => {
      const form = FormBuilder.crearFormularioLista();

      expect(form).toBeInstanceOf(HTMLFormElement);
      expect(form.id).toBe('formCrearLista');
    });

    test('incluye el campo de nombre requerido', () => {
      const form = FormBuilder.crearFormularioLista();
      const input = form.querySelector('input[name="nombre"]');

      expect(input).not.toBeNull();
      expect(input.required).toBe(true);
      expect(input.maxLength).toBe(50);
    });

    test('incluye el icono por defecto en un campo oculto', () => {
      const form = FormBuilder.crearFormularioLista();
      const iconoInput = form.querySelector('input[name="icono"]');

      expect(iconoInput.type).toBe('hidden');
      expect(iconoInput.value).toBe('h-clipboard-document-list');
    });

    test('incluye el color por defecto', () => {
      const form = FormBuilder.crearFormularioLista();
      const colorInput = form.querySelector('input[name="color"]');

      expect(colorInput.value).toBe('#b5551a');
    });

    test('cada llamada devuelve un nodo <form> distinto', () => {
      const form1 = FormBuilder.crearFormularioLista();
      const form2 = FormBuilder.crearFormularioLista();

      expect(form1).not.toBe(form2);
    });
  });

  describe('inyectarFormularioEnModal()', () => {
    test('si el modal no tiene formulario, crea uno y lo añade', () => {
      const modalContent = document.createElement('div');

      const form = FormBuilder.inyectarFormularioEnModal(modalContent);

      expect(modalContent.contains(form)).toBe(true);
      expect(form.id).toBe('formCrearLista');
    });

    test('si el modal ya tiene un formulario, reutiliza el mismo nodo', () => {
      const modalContent = document.createElement('div');
      const formOriginal = document.createElement('form');
      formOriginal.innerHTML = '<p>contenido viejo</p>';
      modalContent.appendChild(formOriginal);

      const formDevuelto = FormBuilder.inyectarFormularioEnModal(modalContent);

      expect(formDevuelto).toBe(formOriginal);
      expect(modalContent.querySelectorAll('form')).toHaveLength(1);
    });

    test('al reutilizar el formulario, rellena de nuevo los campos', () => {
      const modalContent = document.createElement('div');
      const formOriginal = document.createElement('form');
      modalContent.appendChild(formOriginal);

      const formDevuelto = FormBuilder.inyectarFormularioEnModal(modalContent);

      expect(formDevuelto.querySelector('input[name="nombre"]')).not.toBeNull();
    });
  });

  describe('validarFormularioLista()', () => {
    function formConNombre(valor) {
      const form = document.createElement('form');
      form.innerHTML = `<input name="nombre" value="${valor}">`;
      return form;
    }

    test('devuelve true si el nombre tiene contenido', () => {
      const form = formConNombre('Mi lista');

      expect(FormBuilder.validarFormularioLista(form)).toBe(true);
      expect(global.Toast.error).not.toHaveBeenCalled();
    });

    test('devuelve false y avisa si el nombre está vacío', () => {
      const form = formConNombre('');

      expect(FormBuilder.validarFormularioLista(form)).toBe(false);
      expect(global.Toast.error).toHaveBeenCalledWith('El nombre de la lista es requerido');
    });

    test('devuelve false si el nombre es solo espacios en blanco', () => {
      const form = formConNombre('   ');

      expect(FormBuilder.validarFormularioLista(form)).toBe(false);
      expect(global.Toast.error).toHaveBeenCalled();
    });

    test('devuelve false si no existe el campo nombre en absoluto', () => {
      const form = document.createElement('form');

      expect(FormBuilder.validarFormularioLista(form)).toBe(false);
      expect(global.Toast.error).toHaveBeenCalled();
    });
  });
});
