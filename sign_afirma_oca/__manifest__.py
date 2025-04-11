# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sign Afirma",
    "summary": """Integrate OCA Signature with AutoFirma""",
    "version": "16.0.1.0.0",
    "license": "AGPL-3",
    "author": "Dixmit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/sign",
    "depends": [
        "sign_oca",
    ],
    "data": [
        "views/sign_oca_role.xml",
        "views/sign_oca_request_signer.xml",
    ],
    "demo": [],
    "assets": {
        "web.assets_backend": [
            "sign_afirma_oca/static/lib/afirma-autoscript.js",
            "sign_afirma_oca/static/src/components/sign_oca_pdf/*.esm.js",
        ],
        "web.assets_frontend": [
            "sign_afirma_oca/static/lib/afirma-autoscript.js",
            "sign_afirma_oca/static/src/components/sign_oca_pdf_portal/*.esm.js",
        ],
    },
}
