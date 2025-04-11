# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from odoo import api, fields, models


class SignOcaRequestSigner(models.Model):

    _inherit = "sign.oca.request.signer"

    afirma_value = fields.Char(readonly=True)
    afirma_certificate = fields.Char(readonly=True)
    afirma_items = fields.Char(readonly=True)
    afirma_validity = fields.Boolean(compute="_compute_afirma_validity")

    @api.depends("afirma_value", "afirma_certificate", "afirma_items")
    def _compute_afirma_validity(self):
        for record in self:
            record.afirma_validity = record._get_afirma_validity()

    def _get_afirma_validity(self):
        if (
            not self.afirma_certificate
            or not self.afirma_value
            or not self.afirma_items
        ):
            return True
        try:
            cert = x509.load_der_x509_certificate(
                base64.b64decode(self.afirma_certificate)
            )
            public_key = cert.public_key()
            if isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(
                    base64.b64decode(self.afirma_value.encode("utf-8")),
                    self.afirma_items.encode("utf-8"),
                    padding.PKCS1v15(),  # Adjust if a different padding was used
                    hashes.SHA512(),  # Ensure it matches the signing algorithm
                )
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
            return True
        except:
            return False

    def get_info(self, *args, **kwargs):
        result = super().get_info(*args, **kwargs)
        result["afirma"] = self.role_id.afirma
        return result

    def action_sign(
        self,
        *args,
        afirma_value=False,
        afirma_certificate=False,
        afirma_items=False,
        **kwargs
    ):
        res = super().action_sign(
            *args,
            afirma_value=afirma_value,
            afirma_certificate=afirma_certificate,
            **kwargs
        )
        if afirma_value and afirma_certificate and afirma_items:
            self.afirma_value = afirma_value
            self.afirma_certificate = afirma_certificate
            self.afirma_items = afirma_items
        return res
