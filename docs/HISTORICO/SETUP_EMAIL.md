# 📧 Configuración de Email (Opcional)

## ⚠️ IMPORTANTE

El sistema de invitaciones **NO REQUIERE SMTP configurado**. Por defecto:
- Se genera un **enlace copiable** para compartir invitaciones
- El usuario **controla su propio email** (respeta privacidad)
- Funciona sin servidor SMTP centralizado

## Configuración Manual de Email

Si **deseas** usar SMTP (servidor de email centralizado), aquí hay opciones:

---

## 1. GMAIL (Recomendado para Testing)

### Requisitos
- Cuenta Gmail activa
- Contraseña de aplicación (no la contraseña normal)

### Pasos

1. **Habilitar 2FA en Google**
   - Abre https://myaccount.google.com/security
   - Activa "Verificación en dos pasos"

2. **Crear contraseña de aplicación**
   - Ve a https://myaccount.google.com/apppasswords
   - Selecciona:
     - Aplicación: Mail
     - Dispositivo: Windows/Mac/Linux
   - Copia la contraseña generada

3. **Configurar .env**
   ```env
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=tu_email@gmail.com
   SMTP_PASSWORD=xxxx xxxx xxxx xxxx
   SMTP_FROM=tu_email@gmail.com
   ```

4. **Probar**
   ```bash
   python -c "from stockhogar.servicios.email_service import EmailService; EmailService.enviar_invitacion_lista('test@example.com', 'Test', 'Usuario', 'codigo123', 'ver')"
   ```

---

## 2. OUTLOOK / HOTMAIL

### Configuración
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=tu_email@outlook.com
SMTP_PASSWORD=tu_contraseña
SMTP_FROM=tu_email@outlook.com
```

### Notas
- Requiere contraseña normal (no generada)
- Puede rechazar si cree que es "aplicación insegura"
- Solución: Usar contraseña de aplicación si tienes 2FA

---

## 3. SENDGRID (Mejor para Producción)

### Requisitos
- Cuenta en https://sendgrid.com/
- Plan gratuito: hasta 100 emails/día

### Pasos

1. **Crear API Key**
   - Abre https://app.sendgrid.com/settings/api_keys
   - Haz clic en "Create API Key"
   - Nombre: `Dreame`
   - Permiso: "Mail Send"
   - Copia la key

2. **Configurar .env**
   ```env
   SMTP_SERVER=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USER=apikey
   SMTP_PASSWORD=SG.xxxxxxxxxxxxxxxx
   SMTP_FROM=noreply@tudominio.com
   ```

3. **Verificar dominio** (para producción)
   - SendGrid requiere verificación de dominio
   - Sigue instrucciones en dashboard

---

## 4. SELF-HOSTED (Postfix/Dovecot)

Si tienes tu propio servidor:

```env
SMTP_SERVER=mail.tudominio.com
SMTP_PORT=587
SMTP_USER=noreply@tudominio.com
SMTP_PASSWORD=contraseña
SMTP_FROM=noreply@tudominio.com
```

---

## 5. AWS SES (Amazon Simple Email Service)

Para escala grande:

```env
SMTP_SERVER=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=AKIAIOSFODNN7EXAMPLE
SMTP_PASSWORD=BIcsyqKvN4wxB3z...
SMTP_FROM=noreply@tudominio.com
```

---

## RECOMENDACIÓN PARA DESARROLLO

**No configures SMTP en desarrollo**. En su lugar:

1. Usa el **enlace copiable** que genera el sistema
2. Los usuarios ven el enlace y pueden:
   - Compartir por WhatsApp ✅
   - Enviar por email manualmente ✅
   - Usar cualquier medio que deseen ✅

## RECOMENDACIÓN PARA PRODUCCIÓN

Para producción, usa **SendGrid** o **AWS SES**:
- Infraestructura profesional
- Buena entregabilidad
- Soporte técnico
- Métricas de envío

---

## TESTING DEL SERVICIO

Si configuras SMTP, prueba con:

```bash
python
from stockhogar.servicios.email_service import EmailService

# Enviar email de prueba
resultado = EmailService.enviar_invitacion_lista(
    email_destino='tu_email@gmail.com',
    nombre_lista='Mi Lista',
    nombre_remitente='Usuario Prueba',
    codigo_invitacion='prueba123',
    nivel='ver'
)

print(f"Email enviado: {resultado}")
```

---

## SOLUCIONAR PROBLEMAS

### Error: "SMTP connection refused"
- Verifica SMTP_SERVER y SMTP_PORT
- Algunos ISP bloquean puerto 587
- Intenta puerto 25 o 465

### Error: "Authentication failed"
- Verifica SMTP_USER y SMTP_PASSWORD
- Comprueba que no hay espacios
- Para Gmail: usa contraseña de aplicación

### Los emails llegan a SPAM
- Configura SPF/DKIM/DMARC
- Usa dominio propio (no gmail)
- SendGrid/AWS SES tienen mejor reputación

---

## CONCLUSIÓN

**Para desarrollo**: No configures nada, usa enlaces copiables

**Para producción**: Usa SendGrid o AWS SES

El sistema está diseñado para funcionar **sin** SMTP centralizado.
