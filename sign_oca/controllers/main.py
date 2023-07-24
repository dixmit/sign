import base64

from odoo import http
from odoo.http import request

from odoo.addons.base.models.assetsbundle import AssetsBundle


class SignController(http.Controller):
    @http.route("/sign_oca/get_assets.<any(css,js):ext>", type="http", auth="public")
    def get_sign_resources(self, ext):
        xmlid = "sign_oca.sign_assets"
        files, _remains = request.env["ir.qweb"]._get_asset_content(
            xmlid, options=request.context
        )
        asset = AssetsBundle(xmlid, files)
        mock_attachment = getattr(asset, ext)()
        if isinstance(
            mock_attachment, list
        ):  # suppose that CSS asset will not required to be split in pages
            mock_attachment = mock_attachment[0]
        _status, headers, content = request.env["ir.http"].binary_content(
            id=mock_attachment.id, unique=asset.checksum
        )
        content_base64 = base64.b64decode(content) if content else ""
        headers.append(("Content-Length", len(content_base64)))
        return request.make_response(content_base64, headers)
