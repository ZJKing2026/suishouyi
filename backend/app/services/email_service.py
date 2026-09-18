"""邮件发送服务：SMTP。"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header


class EmailService:

    def send(
        self,
        email: str,
        auth_code: str,
        smtp_host: str,
        smtp_port: int,
        to: str,
        subject: str,
        body: str,
    ) -> dict:
        """发送纯文本邮件。"""
        if not email or not auth_code:
            raise ValueError("未配置邮箱或授权码")

        msg = MIMEMultipart()
        msg["From"] = email
        msg["To"] = to
        msg["Subject"] = Header(subject, "utf-8")
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
                server.starttls()

            server.login(email, auth_code)
            server.send_message(msg)
            server.quit()

            return {"success": True, "message": f"邮件已发送至 {to}"}

        except smtplib.SMTPAuthenticationError:
            raise ValueError("邮箱或授权码错误。请确认使用了授权码（不是登录密码）")
        except smtplib.SMTPException as e:
            raise ValueError(f"发送失败：{str(e)}")
        except Exception as e:
            raise ValueError(f"网络错误：{str(e)}")


email_service = EmailService()