# Copyright 2023 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from base64 import b64decode, b64encode
from io import BytesIO

from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SignOcaRequest(models.Model):

    _name = "sign.oca.request"
    _description = "Sign Request"

    template_id = fields.Many2one("sign.oca.template")
    data = fields.Binary(related="template_id.data")
    signed = fields.Boolean()
    signed_data = fields.Binary(readonly=True)
    item_ids = fields.One2many("sign.oca.request.field", inverse_name="request_id")
    signer_ids = fields.One2many("sign.oca.request.signer", inverse_name="request_id")
    to_sign = fields.Boolean(compute="_compute_to_sign")

    @api.depends("signer_ids.role_id", "item_ids.item_id.required")
    @api.depends_context("uid")
    def _compute_to_sign(self):
        for record in self:
            roles = record.signer_ids.filtered(
                lambda r: r.partner_id.id == self.env.user.partner_id.id
                and not r.signed
            ).mapped("role_id")
            record.to_sign = (
                len(record.item_ids.filtered(lambda r: r.item_id.role_id in roles)) > 0
            )

    def action_sign(self, partner_id=False):
        self.ensure_one()
        if not partner_id:
            partner_id = self.env.user.partner_id.id
        signers = self.signer_ids.filtered(
            lambda r: r.partner_id.id == partner_id and not r.signed
        )
        items = self.item_ids.filtered(lambda r: r.signer_id in signers)
        items.check_signable()
        signers.write({"signed": True})
        self._full_sign()
        return True

    def _full_sign(self):
        if self.signer_ids.filtered(lambda r: not r.signed):
            return

        input_data = BytesIO(b64decode(self.template_id.data))
        reader = PdfFileReader(input_data)
        output = PdfFileWriter()
        for page_number in range(1, reader.numPages + 1):
            page = reader.getPage(page_number - 1)
            for item in self.item_ids.filtered(lambda r: r.item_id.page == page_number):
                new_page = item._get_pdf_page(page.mediaBox)
                if new_page:
                    page.mergePage(new_page)
            output.addPage(page)

        output_stream = BytesIO()
        output.write(output_stream)

        # env["sign.oca.request"].browse(12).action_sign()

        output_stream.seek(0)
        self.write({"signed_data": b64encode(output_stream.read())})

    def sign(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "sign_oca",
            "name": self.template_id.name,
            "params": {
                "res_model": self._name,
                "res_id": self.id,
            },
        }

    def get_info(self, partner=None):
        self.ensure_one()
        if not partner:
            partner = self.env.user.partner_id
        result = {
            "name": self.template_id.name,
            "items": {},
            "to_sign": self.to_sign,
            "partner": {
                "id": partner.id,
                "name": partner.name,
                "email": partner.email,
                "phone": partner.phone,
            },
            "roles": {
                signer.role_id.id: {
                    "id": signer.id,
                    "name": signer.role_id.name,
                    "role_id": signer.role_id.id,
                    "partner_id": signer.partner_id.id,
                }
                for signer in self.signer_ids
            },
        }
        items = sorted(
            self.item_ids,
            key=lambda item: (
                item.item_id.page,
                item.item_id.position_y,
                item.item_id.position_x,
            ),
        )
        tabindex = 1
        for item in items:
            item_data = item.get_info()
            item_data["tabindex"] = tabindex
            item_data["to_sign"] = (
                result["roles"][item.item_id.role_id.id]["partner_id"] == partner.id
            )
            tabindex += 1
            result["items"][item.id] = item_data
        return result


class SignOcaRequestField(models.Model):
    _name = "sign.oca.request.field"
    _description = "Sign Request Value"

    request_id = fields.Many2one("sign.oca.request", required=True)
    item_id = fields.Many2one("sign.oca.template.item", required=True)
    signer_id = fields.Many2one("sign.oca.request.signer")
    value_text = fields.Char()
    value_binary = fields.Binary()

    def check_signable(self):
        for record in self:
            record._check_signable()

    def _check_signable(self):
        if not self.item_id.required:
            return
        if self.item_id.field_id.field_type == "text" and not self.value_text:
            raise ValidationError(
                _("Field %s is not filled") % self.item_id.field_id.display_name
            )

    def get_info(self):
        self.ensure_one()
        return {
            "id": self.id,
            "field_id": self.item_id.field_id.id,
            "field_type": self.item_id.field_id.field_type,
            "required": self.item_id.required,
            "name": self.item_id.field_id.name,
            "role": self.item_id.role_id.id,
            "page": self.item_id.page,
            "position_x": self.item_id.position_x,
            "position_y": self.item_id.position_y,
            "width": self.item_id.width,
            "height": self.item_id.height,
            "value_text": self.value_text,
            "value_binary": self.value_binary
            and "data:image/png;base64,%s" % self.value_binary.decode("utf-8"),
            "default_value": self.item_id.field_id.default_value,
        }

    def _get_pdf_page_text(self, box):
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=(box.getWidth(), box.getHeight()))
        if not self.value_text:
            return False
        par = Paragraph(self.value_text)
        par.wrap(
            self.item_id.width / 100 * float(box.getWidth()),
            self.item_id.height / 100 * float(box.getHeight()),
        )
        par.drawOn(
            can,
            self.item_id.position_x / 100 * float(box.getWidth()),
            (100 - self.item_id.position_y - self.item_id.height)
            / 100
            * float(box.getHeight()),
        )
        can.save()
        packet.seek(0)
        new_pdf = PdfFileReader(packet)
        return new_pdf.getPage(0)

    def _get_pdf_page_signature(self, box):
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=(box.getWidth(), box.getHeight()))
        if not self.value_binary:
            return False
        par = Image(
            BytesIO(b64decode(self.value_binary)),
            width=self.item_id.width / 100 * float(box.getWidth()),
            height=self.item_id.height / 100 * float(box.getHeight()),
        )
        par.drawOn(
            can,
            self.item_id.position_x / 100 * float(box.getWidth()),
            (100 - self.item_id.position_y - self.item_id.height)
            / 100
            * float(box.getHeight()),
        )
        can.save()
        packet.seek(0)
        new_pdf = PdfFileReader(packet)
        return new_pdf.getPage(0)

    def _get_pdf_page(self, box):
        return getattr(self, "_get_pdf_page_%s" % self.item_id.field_id.field_type)(box)


class SignOcaRequestSigner(models.Model):

    _name = "sign.oca.request.signer"
    _inherit = "portal.mixin"
    _description = "Sign Request Value"

    request_id = fields.Many2one("sign.oca.request", required=True)
    partner_id = fields.Many2one("res.partner", required=True)
    role_id = fields.Many2one("sign.oca.role", required=True)
    signed = fields.Boolean()
