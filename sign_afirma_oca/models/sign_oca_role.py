# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SignOcaRole(models.Model):

    _inherit = "sign.oca.role"

    afirma = fields.Selection(
        [
            ("verify", "Verify with Autofirma"),
            ("sign", "Sign with Autofirma"),
        ],
    )
