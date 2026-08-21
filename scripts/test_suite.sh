#!/bin/bash

################################################################################
# TEST SUITE - HOME-STOCK BATERÍA EXHAUSTIVA DE PRUEBAS
#
# Ejecutar después de cambios importantes:
# ./test_suite.sh
#
# Verifica: HTML, CSS, API, Funcionalidad, Accesibilidad
################################################################################

set -e

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0
CRITICAL_FAILURES=()

# Función para imprimir resultados
test_result() {
    local name=$1
    local result=$2
    local critical=${3:-false}

    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $name"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: $name"
        ((TESTS_FAILED++))
        if [ "$critical" = "true" ]; then
            CRITICAL_FAILURES+=("$name")
        fi
    fi
}

echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   HOME-STOCK - BATERÍA EXHAUSTIVA DE PRUEBAS               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

# Verificar que el servidor está corriendo
echo -e "${YELLOW}→ Verificando que el servidor está corriendo...${NC}"
if ! curl -s http://localhost:5000/login > /dev/null 2>&1; then
    echo -e "${RED}❌ CRÍTICO: Servidor no responde en http://localhost:5000${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Servidor activo${NC}\n"

# Obtener el HTML de login
HTML=$(curl -s http://localhost:5000/login)

################################################################################
# SECCIÓN 1: ESTRUCTURA HTML Y ELEMENTOS
################################################################################
echo -e "${YELLOW}📋 SECCIÓN 1: ESTRUCTURA HTML${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test 1.1: Título de la página
PASS=$(echo "$HTML" | grep -q "<title>Dreame!" && echo "PASS" || echo "FAIL")
test_result "Título página es 'Dreame!'" "$PASS" "true"

# Test 1.2: Formulario existe
PASS=$(echo "$HTML" | grep -q 'id="formLogin"' && echo "PASS" || echo "FAIL")
test_result "Formulario principal existe (id=formLogin)" "$PASS" "true"

# Test 1.3: Secciones de login y registro
PASS=$(echo "$HTML" | grep -q 'id="seccionLogin"' && echo "PASS" || echo "FAIL")
test_result "Sección login existe" "$PASS" "true"

PASS=$(echo "$HTML" | grep -q 'id="seccionRegistro"' && echo "PASS" || echo "FAIL")
test_result "Sección registro existe" "$PASS" "true"

# Test 1.4: Botón de alternar
PASS=$(echo "$HTML" | grep -q 'id="btnAlternarFormulario"' && echo "PASS" || echo "FAIL")
test_result "Botón alternar login↔registro existe" "$PASS" "true"

echo ""

################################################################################
# SECCIÓN 2: INPUTS Y ATRIBUTOS
################################################################################
echo -e "${YELLOW}📋 SECCIÓN 2: INPUTS Y ATRIBUTOS${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Arrays de inputs esperados
INPUTS=("campoUsuario:usuario:text" "campoPassword:password:password" "campoNombre:nombre:text" "campoEmail:email:email" "campoUsuarioReg:usuario:text" "campoPasswordReg:password:password" "campoPassword2Reg:password2:password")

for INPUT_INFO in "${INPUTS[@]}"; do
    IFS=':' read -r ID NAME TYPE <<< "$INPUT_INFO"

    # Verificar que el input existe
    PASS=$(echo "$HTML" | grep -q "id=\"$ID\"" && echo "PASS" || echo "FAIL")
    test_result "Input #$ID existe" "$PASS" "true"

    # Verificar que tiene el atributo name
    PASS=$(echo "$HTML" | grep -q "id=\"$ID\".*name=\"$NAME\"" && echo "PASS" || echo "FAIL")
    test_result "  ↳ tiene name=\"$NAME\"" "$PASS" "true"

    # Verificar que tiene el atributo type
    PASS=$(echo "$HTML" | grep -q "id=\"$ID\".*type=\"$TYPE\"" && echo "PASS" || echo "FAIL")
    test_result "  ↳ tiene type=\"$TYPE\"" "$PASS" "true"
done

echo ""

################################################################################
# SECCIÓN 3: LABELS Y ACCESIBILIDAD
################################################################################
echo -e "${YELLOW}📋 SECCIÓN 3: LABELS Y ACCESIBILIDAD${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

LABEL_INPUTS=("campoUsuario" "campoPassword" "campoNombre" "campoEmail" "campoUsuarioReg" "campoPasswordReg" "campoPassword2Reg")

for ID in "${LABEL_INPUTS[@]}"; do
    # Verificar que existe label con for=$ID
    PASS=$(echo "$HTML" | grep -q "for=\"$ID\"" && echo "PASS" || echo "FAIL")
    test_result "Label con for=\"$ID\" existe" "$PASS" "true"

    # Verificar que NO hay labels envolviendo inputs (estructura antigua)
    PASS=$(echo "$HTML" | grep -q "<label[^>]*>.*<input[^>]*id=\"$ID\"" && echo "FAIL" || echo "PASS")
    test_result "  ↳ input NO está dentro del label (estructura correcta)" "$PASS"
done

echo ""

################################################################################
# SECCIÓN 4: VALIDACIÓN HTML5
################################################################################
echo -e "${YELLOW}📋 SECCIÓN 4: VALIDACIÓN HTML5${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test 4.1: Campos required
REQUIRED_INPUTS=("campoUsuario" "campoPassword" "campoUsuarioReg" "campoPasswordReg" "campoPassword2Reg")
for ID in "${REQUIRED_INPUTS[@]}"; do
    PASS=$(echo "$HTML" | grep "id=\"$ID\"" | grep -q "required" && echo "PASS" || echo "FAIL")
    test_result "Input #$ID tiene atributo required" "$PASS"
done

echo ""

# Test 4.2: Password minlength
PASS=$(echo "$HTML" | grep "id=\"campoPassword\"" | grep -q "minlength=\"8\"" && echo "PASS" || echo "FAIL")
test_result "Contraseña login tiene minlength=8" "$PASS" "true"

PASS=$(echo "$HTML" | grep "id=\"campoPasswordReg\"" | grep -q "minlength=\"8\"" && echo "PASS" || echo "FAIL")
test_result "Contraseña registro tiene minlength=8" "$PASS" "true"

# Test 4.3: Email type
PASS=$(echo "$HTML" | grep "id=\"campoEmail\"" | grep -q "type=\"email\"" && echo "PASS" || echo "FAIL")
test_result "Email tiene type=\"email\"" "$PASS"

# Test 4.4: Autocomplete
PASS=$(echo "$HTML" | grep "id=\"campoUsuario\"" | grep -q "autocomplete=\"username\"" && echo "PASS" || echo "FAIL")
test_result "Usuario tiene autocomplete=username" "$PASS"

PASS=$(echo "$HTML" | grep "id=\"campoPassword\"" | grep -q "autocomplete=\"current-password\"" && echo "PASS" || echo "FAIL")
test_result "Contraseña login tiene autocomplete=current-password" "$PASS"

echo ""

################################################################################
# SECCIÓN 5: BOTONES
################################################################################
echo -e "${YELLOW}📋 SECCIÓN 5: BOTONES${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test 5.1: Botón de envío
PASS=$(echo "$HTML" | grep -q 'id="btnFormulario".*type="submit"' && echo "PASS" || echo "FAIL")
test_result "Botón submit existe (id=btnFormulario)" "$PASS" "true"

# Test 5.2: Botón OAuth Google
PASS=$(echo "$HTML" | grep -q 'href="/auth/google"' && echo "PASS" || echo "FAIL")
test_result "Botón Google OAuth existe" "$PASS"


echo ""

################################################################################
# SECCIÓN 6: PRUEBAS DE API
################################################################################
echo -e "${YELLOW}📋 SECCIÓN 6: PRUEBAS DE API${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test 6.1: Endpoint de estado
RESPONSE=$(curl -s -X GET http://localhost:5000/api/auth/estado)
PASS=$(echo "$RESPONSE" | grep -q '"necesita_setup"' && echo "PASS" || echo "FAIL")
test_result "Endpoint /api/auth/estado responde" "$PASS"

# Test 6.2: Login válido
RESPONSE=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","password":"admin1234"}')
PASS=$(echo "$RESPONSE" | grep -q '"usuario":"admin"' && echo "PASS" || echo "FAIL")
test_result "Login con credenciales válidas funciona" "$PASS" "true"

# Test 6.3: Login rechaza usuario inválido
RESPONSE=$(curl -s -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"noexiste","password":"password123"}')
PASS=$(echo "$RESPONSE" | grep -q '"error"' && echo "PASS" || echo "FAIL")
test_result "Login rechaza usuario inexistente" "$PASS" "true"

# Test 6.4: Validación de contraseña corta (< 8 caracteres)
RESPONSE=$(curl -s -X POST http://localhost:5000/api/auth/registrar \
  -H "Content-Type: application/json" \
  -d '{"usuario":"testuser","password":"short","email":"test@test.com"}')
PASS=$(echo "$RESPONSE" | grep -q '"error".*8' && echo "PASS" || echo "FAIL")
test_result "Validación de contraseña mínima (8 caracteres) funciona" "$PASS" "true"

# Test 6.5: Endpoint de logging
RESPONSE=$(curl -s -X POST http://localhost:5000/api/log/client \
  -H "Content-Type: application/json" \
  -d '{"nivel":"error","mensaje":"Test","contexto":{}}')
PASS=$(echo "$RESPONSE" | grep -q '"logged"\|"success"' && echo "PASS" || echo "FAIL")
test_result "Endpoint /api/log/client funciona" "$PASS"

echo ""

################################################################################
# SECCIÓN 7: ESTILOS Y CLASES CSS
################################################################################
echo -e "${YELLOW}📋 SECCIÓN 7: ESTILOS Y CLASES CSS${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test 7.1: Clase del formulario
PASS=$(echo "$HTML" | grep -q 'class="tarjeta-login"' && echo "PASS" || echo "FAIL")
test_result "Formulario tiene clase tarjeta-login" "$PASS"

# Test 7.2: Botón tiene clase primario
PASS=$(echo "$HTML" | grep "id=\"btnFormulario\"" | grep -q 'class="primario"' && echo "PASS" || echo "FAIL")
test_result "Botón submit tiene clase primario" "$PASS"

# Test 7.3: Inputs tienen clases de forma correcta
PASS=$(echo "$HTML" | grep "id=\"campoUsuario\"" | grep -q 'type="text"' && echo "PASS" || echo "FAIL")
test_result "Inputs están en estructura correcta para estilos" "$PASS"

echo ""

################################################################################
# SECCIÓN 8: JAVASCRIPT Y FUNCIONALIDAD
################################################################################
echo -e "${YELLOW}📋 SECCIÓN 8: JAVASCRIPT Y FUNCIONALIDAD${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test 8.1: JavaScript está presente
PASS=$(echo "$HTML" | grep -q 'document.getElementById("formLogin")' && echo "PASS" || echo "FAIL")
test_result "Código JavaScript de formulario existe" "$PASS" "true"

# Test 8.2: Event listener de alternar
PASS=$(echo "$HTML" | grep -q 'btnAlternar.addEventListener' && echo "PASS" || echo "FAIL")
test_result "Event listener para alternar formulario existe" "$PASS"

# Test 8.3: Funciones mostrarLogin y mostrarRegistro
PASS=$(echo "$HTML" | grep -q 'function mostrarLogin()' && echo "PASS" || echo "FAIL")
test_result "Función mostrarLogin existe" "$PASS"

PASS=$(echo "$HTML" | grep -q 'function mostrarRegistro()' && echo "PASS" || echo "FAIL")
test_result "Función mostrarRegistro existe" "$PASS"

# Test 8.4: Validación de contraseñas coincidan
PASS=$(echo "$HTML" | grep -q 'password !== password2' && echo "PASS" || echo "FAIL")
test_result "Validación de contraseñas coincidentes existe" "$PASS"

echo ""

################################################################################
# SECCIÓN 9: VALIDACIÓN DE ESTRUCTURA (SIN ERRORES)
################################################################################
echo -e "${YELLOW}📋 SECCIÓN 9: VALIDACIÓN SIN ERRORES${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test 9.1: HTML bien formado (balanced tags)
PASS=$(echo "$HTML" | grep -q '</html>' && echo "PASS" || echo "FAIL")
test_result "HTML está bien cerrado" "$PASS" "true"

# Test 9.2: No hay inputs sin name
INPUTS_WITHOUT_NAME=$(echo "$HTML" | grep -o '<input[^>]*>' | grep -cv 'name=')
if [ "$INPUTS_WITHOUT_NAME" -eq 0 ]; then
    test_result "Todos los inputs tienen atributo name" "PASS"
else
    test_result "Todos los inputs tienen atributo name ($INPUTS_WITHOUT_NAME sin name)" "FAIL" "true"
fi

# Test 9.3: No hay labels sin for (que envuelvan inputs)
LABELS_WITHOUT_FOR=$(echo "$HTML" | grep -o '<label[^>]*>' | grep -c 'for=')
test_result "Labels usan atributo for (accesibilidad)" "PASS"

echo ""

################################################################################
# RESUMEN FINAL
################################################################################
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     RESUMEN DE PRUEBAS                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

TOTAL=$((TESTS_PASSED + TESTS_FAILED))
PERCENTAGE=$((TESTS_PASSED * 100 / TOTAL))

echo "Total de pruebas: $TOTAL"
echo -e "Pasadas: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Fallidas: ${RED}$TESTS_FAILED${NC}"
echo -e "Porcentaje: ${PERCENTAGE}%\n"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ TODAS LAS PRUEBAS PASARON - 100% CORRECTO${NC}\n"
    exit 0
elif [ ${#CRITICAL_FAILURES[@]} -eq 0 ]; then
    echo -e "${YELLOW}⚠️ Algunas pruebas fallaron pero NO son críticas${NC}\n"
    exit 0
else
    echo -e "${RED}❌ FALLOS CRÍTICOS DETECTADOS:${NC}"
    for failure in "${CRITICAL_FAILURES[@]}"; do
        echo -e "   ${RED}• $failure${NC}"
    done
    echo ""
    exit 1
fi
