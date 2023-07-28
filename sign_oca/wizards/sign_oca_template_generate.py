# Copyright 2023 CreuBlana
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class SignOcaTemplateGenerate(models.TransientModel):

    _name = "sign.oca.template.generate"
    _description = "Generate a signature request"

    def _default_signers(self):
        template = self.env["sign.oca.template"].browse(
            self.env.context.get("default_template_id")
        )
        if not template:
            return []
        return [(0, 0, {"role_id": role.id}) for role in template.item_ids.role_id]

    template_id = fields.Many2one("sign.oca.template")
    signer_ids = fields.One2many(
        "sign.oca.template.generate.signer",
        inverse_name="wizard_id",
        default=lambda r: r._default_signers(),
    )
    sign_now = fields.Boolean()
    message = fields.Html()

    def _generate_vals(self):
        return {
            "template_id": self.template_id.id,
            "item_ids": [
                (
                    0,
                    0,
                    {
                        "item_id": item.id,
                    },
                )
                for item in self.template_id.item_ids
            ],
            "signer_ids": [
                (
                    0,
                    0,
                    {
                        "partner_id": signer.partner_id.id,
                        "role_id": signer.role_id.id,
                    },
                )
                for signer in self.signer_ids
            ],
        }

    def _generate(self):
        return self.env["sign.oca.request"].create(self._generate_vals())

    def generate(self):
        request = self._generate()
        for signer in request.signer_ids:
            signer._portal_ensure_token()
            if self.sign_now and signer.partner_id == self.env.user.partner_id:
                continue
            view = self.env.ref("sign_oca.sign_oca_template_mail")
            render_result = view._render(
                {"record": signer, "body": self.message, "link": signer.access_url},
                engine="ir.qweb",
                minimal_qcontext=True,
            )
            self.env["mail.thread"].message_notify(
                body=render_result,
                partner_ids=signer.partner_id.ids,
                subject=_("New document to sign"),
                subtype_id=self.env.ref("mail.mt_comment").id,
                mail_auto_delete=False,
                email_layout_xmlid="mail.mail_notification_light",
            )
        return request.sign


class SignOcaTemplateGenerateSigner(models.TransientModel):
    _name = "sign.oca.template.generate.signer"
    _description = "Signature request signers"

    def _get_default_partner(self):
        if self.env.context.get("default_sign_now"):
            return self.env.user.partner_id
        return False

    wizard_id = fields.Many2one("sign.oca.template.generate.signer")
    role_id = fields.Many2one("sign.oca.role", required=True, readonly=True)
    partner_id = fields.Many2one(
        "res.partner", required=True, default=lambda r: r._get_default_partner()
    )
