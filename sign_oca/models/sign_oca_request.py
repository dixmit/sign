# Copyright 2023 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
from base64 import b64decode, b64encode
from io import BytesIO

from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, Paragraph

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SignOcaRequest(models.Model):

    _name = "sign.oca.request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Sign Request"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    template_id = fields.Many2one("sign.oca.template")
    data = fields.Binary(required=True)
    signed = fields.Boolean()
    signed_data = fields.Binary(readonly=True)
    signer_ids = fields.One2many(
        "sign.oca.request.signer", inverse_name="request_id", auto_join=True
    )
    state = fields.Selection(
        [("sent", "Sent"), ("signed", "Signed"), ("cancel", "Cancelled")],
        default="sent",
        required=True,
    )
    signed_count = fields.Integer(compute="_compute_signed_count")
    signer_count = fields.Integer(compute="_compute_signer_count")
    to_sign = fields.Boolean(compute="_compute_to_sign")
    signatory_data = fields.Serialized(default=lambda r: {}, readonly=True)
    current_hash = fields.Char(readonly=True)
    company_id = fields.Many2one(
        "res.company", default=lambda r: r.env.company.id, required=True
    )

    def cancel(self):
        self.write({"state": "cancel"})

    @api.depends("signer_ids")
    def _compute_signer_count(self):
        for record in self:
            record.signer_count = len(record.signer_ids)

    @api.depends("signer_ids", "signer_ids.signed_on")
    def _compute_signed_count(self):
        for record in self:
            record.signed_count = len(record.signer_ids.filtered(lambda r: r.signed_on))

    @api.depends("signer_ids.role_id", "signatory_data")
    @api.depends_context("uid")
    def _compute_to_sign(self):
        for record in self:
            record.to_sign = record.signer_ids.filtered(
                lambda r: r.partner_id.id == self.env.user.partner_id.id
                and not r.signed_on
            ).mapped("role_id")

    def _check_signed(self):
        self.ensure_one()
        if self.state != "sent":
            return
        if all(self.mapped("signer_ids.signed_on")):
            self.state = "signed"

    def sign(self):
        self.ensure_one()
        signer = self.signer_ids.filtered(
            lambda r: r.partner_id == self.env.user.partner_id
        )
        if not signer:
            return self.get_formview_action()
        return {
            "type": "ir.actions.client",
            "tag": "sign_oca",
            "name": self.template_id.name,
            "params": {
                "res_model": signer[0]._name,
                "res_id": signer[0].id,
            },
        }


class SignOcaRequestSigner(models.Model):

    _name = "sign.oca.request.signer"
    _inherit = "portal.mixin"
    _description = "Sign Request Value"

    data = fields.Binary(related="request_id.data")
    request_id = fields.Many2one("sign.oca.request", required=True, ondelete="cascade")
    partner_name = fields.Char(related="partner_id.name")
    partner_id = fields.Many2one("res.partner", required=True, ondelete="restrict")
    role_id = fields.Many2one("sign.oca.role", required=True, ondelete="restrict")
    signed_on = fields.Datetime(readonly=True)
    signature_hash = fields.Char(readonly=True)

    def _compute_access_url(self):
        super()._compute_access_url()
        for record in self:
            record.access_url = "/sign_oca/document/%s/%s" % (
                record.id,
                record.access_token,
            )

    def get_info(self):
        self.ensure_one()
        # TODO: Add a log

        return {
            "role": self.role_id.id if not self.signed_on else False,
            "name": self.request_id.template_id.name,
            "items": self.request_id.signatory_data,
            "to_sign": self.request_id.to_sign,
            "partner": {
                "id": self.env.user.partner_id.id,
                "name": self.env.user.partner_id.name,
                "email": self.env.user.partner_id.email,
                "phone": self.env.user.partner_id.phone,
            },
        }

    def action_sign(self, items):
        self.ensure_one()
        if self.signed_on:
            raise ValidationError(
                _("Users %s has already signed the document") % self.partner_id.name
            )
        if self.request_id.state != "sent":
            raise ValidationError(_("Request cannot be signed"))
        self.signed_on = fields.Datetime.now()
        # current_hash = self.request_id.current_hash
        signatory_data = self.request_id.signatory_data

        input_data = BytesIO(b64decode(self.request_id.data))
        reader = PdfFileReader(input_data)
        output = PdfFileWriter()
        pages = {}
        for page_number in range(1, reader.numPages + 1):
            pages[page_number] = reader.getPage(page_number - 1)

        for key in signatory_data:
            if signatory_data[key]["role"] == self.role_id.id:
                signatory_data[key] = items[key]
                self._check_signable(items[key])
                item = items[key]
                page = pages[item["page"]]
                new_page = self._get_pdf_page(item, page.mediaBox)
                if new_page:
                    page.mergePage(new_page)
                pages[item["page"]] = page
        for page_number in pages:
            output.addPage(pages[page_number])
        output_stream = BytesIO()
        output.write(output_stream)
        output_stream.seek(0)
        signed_pdf = output_stream.read()
        final_hash = hashlib.sha1(signed_pdf).hexdigest()
        # TODO: Review that the hash has not been changed...
        # TODO: Add a log
        self.request_id.write(
            {
                "data": b64encode(signed_pdf),
                "current_hash": final_hash,
            }
        )
        self.signature_hash = final_hash
        self.request_id._check_signed()
        # TODO: Add a return

    def _check_signable(self, item):
        if not item["required"]:
            return
        if not item["value"]:
            raise ValidationError(_("Field %s is not filled") % item["name"])

    def _get_pdf_page_text(self, item, box):
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=(box.getWidth(), box.getHeight()))
        if not item["value"]:
            return False
        par = Paragraph(item["value"], style=self.getParagraphStyle())
        par.wrap(
            item["width"] / 100 * float(box.getWidth()),
            item["height"] / 100 * float(box.getHeight()),
        )
        par.drawOn(
            can,
            item["position_x"] / 100 * float(box.getWidth()),
            (100 - item["position_y"] - item["height"]) / 100 * float(box.getHeight()),
        )
        can.save()
        packet.seek(0)
        new_pdf = PdfFileReader(packet)
        return new_pdf.getPage(0)

    def getParagraphStyle(self):
        return ParagraphStyle(name="Oca Sign Style")

    def _get_pdf_page_signature(self, item, box):
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=(box.getWidth(), box.getHeight()))
        if not item["value"]:
            return False
        par = Image(
            BytesIO(b64decode(item["value"])),
            width=item["width"] / 100 * float(box.getWidth()),
            height=item["height"] / 100 * float(box.getHeight()),
        )
        par.drawOn(
            can,
            item["position_x"] / 100 * float(box.getWidth()),
            (100 - item["position_y"] - item["height"]) / 100 * float(box.getHeight()),
        )
        can.save()
        packet.seek(0)
        new_pdf = PdfFileReader(packet)
        return new_pdf.getPage(0)

    def _get_pdf_page(self, item, box):
        return getattr(self, "_get_pdf_page_%s" % item["field_type"])(item, box)
