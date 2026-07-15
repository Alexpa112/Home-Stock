"""Servicio de email para notificaciones de invitación a listas compartidas."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from ..config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, APP_URL

logger = logging.getLogger(__name__)


class EmailService:
    """Servicio para enviar emails de invitación."""

    @staticmethod
    def enviar_invitacion_lista(
        email_destino: str,
        nombre_lista: str,
        nombre_remitente: str,
        codigo_invitacion: str,
        nivel: str = "ver"
    ) -> bool:
        """
        Envía email de invitación para compartir una lista.

        Args:
            email_destino: Email del destinatario
            nombre_lista: Nombre de la lista compartida
            nombre_remitente: Nombre del usuario que invita
            codigo_invitacion: Código único de invitación
            nivel: Nivel de permiso ('ver' o 'editar')

        Returns:
            True si se envió correctamente, False en caso de error
        """
        if not SMTP_USER or not SMTP_PASSWORD:
            logger.warning("Email no configurado: SMTP_USER o SMTP_PASSWORD vacío")
            return False

        try:
            enlace_invitacion = f"{APP_URL}/aceptar-invitacion/{codigo_invitacion}"

            asunto = f"Te han compartido la lista '{nombre_lista}' en Dreame!"
            cuerpo_html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                    <h2>📦 ¡Bienvenido a Dreame!</h2>

                    <p><strong>{nombre_remitente}</strong> te ha compartido la lista de la compra <strong>"{nombre_lista}"</strong>.</p>

                    <p>Nivel de acceso: <strong>{EmailService._traducir_nivel(nivel)}</strong></p>

                    <p style="margin: 24px 0;">
                        <a href="{enlace_invitacion}"
                           style="display: inline-block; background-color: #B5551A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                            Aceptar invitación
                        </a>
                    </p>

                    <p style="color: #666; font-size: 14px;">
                        Si no puedes hacer clic en el botón, copia y pega este enlace en tu navegador:<br>
                        <code style="background: #f5f5f5; padding: 8px; display: inline-block; margin-top: 8px;">
                            {enlace_invitacion}
                        </code>
                    </p>

                    <hr style="border: none; border-top: 1px solid #ddd; margin: 24px 0;">

                    <p style="color: #999; font-size: 12px;">
                        Esta invitación expirará en 7 días.<br>
                        Dreame! - Tu gestor de listas compartidas
                    </p>
                </body>
            </html>
            """

            return EmailService._enviar_smtp(
                email_destino=email_destino,
                asunto=asunto,
                cuerpo_html=cuerpo_html
            )

        except Exception as e:
            logger.error(f"Error enviando invitación a {email_destino}: {str(e)}")
            return False

    @staticmethod
    def _traducir_nivel(nivel: str) -> str:
        """Traduce código de nivel a texto legible."""
        traducciones = {
            "ver": "Ver (solo lectura)",
            "editar": "Editar (lectura y escritura)"
        }
        return traducciones.get(nivel, nivel)

    @staticmethod
    def _enviar_smtp(email_destino: str, asunto: str, cuerpo_html: str) -> bool:
        """Envía email usando SMTP."""
        try:
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['Subject'] = asunto
            msg['From'] = SMTP_FROM
            msg['To'] = email_destino

            # Adjuntar HTML
            part_html = MIMEText(cuerpo_html, 'html')
            msg.attach(part_html)

            # Enviar
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email enviado a {email_destino}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("Error de autenticación SMTP: Usuario o contraseña incorrectos")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"Error SMTP: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error enviando email: {str(e)}")
            return False
