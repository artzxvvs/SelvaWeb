import base64
import io
from decimal import Decimal

import qrcode
from django.conf import settings
from django.core.mail import send_mail
from django.utils.crypto import get_random_string


def generate_verification_code(length: int = 6) -> str:
    allowed = "0123456789"
    return get_random_string(length=length, allowed_chars=allowed)


def send_verification_email(user, code: str) -> None:
    subject = "Seu código de verificação SelvaCore"
    message = (
        "Obrigado por se cadastrar na SelvaCore!\\n\\n"
        "Use o código abaixo para confirmar seu e-mail e liberar o portal da comunidade:\\n"
        f"Código: {code}\\n\\n"
        "O código expira em 30 minutos. Caso não tenha sido você, ignore esta mensagem."
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)


def _emv_field(field_id: str, value: str) -> str:
    length = f"{len(value):02d}"
    return f"{field_id}{length}{value}"


def _sanitize_text(value: str, limit: int) -> str:
    sanitized = (value or "").strip().upper()
    return sanitized[:limit]


def _crc16(payload: str) -> str:
    polynomial = 0x1021
    result = 0xFFFF
    for char in payload:
        result ^= ord(char) << 8
        for _ in range(8):
            if result & 0x8000:
                result = (result << 1) ^ polynomial
            else:
                result <<= 1
            result &= 0xFFFF
    return f"{result:04X}"


def build_pix_payload(*, key: str, txid: str, amount: Decimal, merchant_name: str, merchant_city: str, description: str = "") -> str:
    """Gera payload EMV para Pix estático seguindo o manual do Bacen."""
    merchant_account_info = (
        _emv_field("00", "BR.GOV.BCB.PIX")
        + _emv_field("01", key.strip())
    )
    if description:
        merchant_account_info += _emv_field("02", description[:20])

    merchant_account = _emv_field("26", merchant_account_info)
    transaction_amount = _emv_field("54", f"{Decimal(amount):.2f}")

    additional_data = _emv_field("05", txid[:25])
    additional = _emv_field("62", additional_data)

    payload = (
        _emv_field("00", "01")
        + _emv_field("01", "12")
        + merchant_account
        + _emv_field("52", "0000")
        + _emv_field("53", "986")
        + transaction_amount
        + _emv_field("58", "BR")
        + _emv_field("59", _sanitize_text(merchant_name, 25))
        + _emv_field("60", _sanitize_text(merchant_city, 15))
        + additional
    )

    payload_to_crc = payload + "6304"
    crc = _crc16(payload_to_crc)
    return payload_to_crc + crc


def qr_code_base64(data: str) -> str:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")
    #End of File