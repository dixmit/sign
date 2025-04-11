/** @odoo-module */
/* global AutoScript */

import {SignOcaPdfPortal} from "@sign_oca/components/sign_oca_pdf_portal/sign_oca_pdf_portal.esm";
import {patch} from "@web/core/utils/patch";

patch(SignOcaPdfPortal.prototype, "sign_afirma", {
    async _onClickSign({skipAfirma = false}) {
        if (!skipAfirma && this.onSignatureProcess) {
            return;
        }
        if (!skipAfirma && this.info.afirma === "verify") {
            this.onSignatureProcess = true;
            AutoScript.cargarAppAfirma();
            return AutoScript.sign(
                AutoScript.getBase64FromText(this._getAfirmaSignedData()),
                "SHA512withRSA",
                "CAdES",
                "mode=implicit",
                this._onAfirmaSign.bind(this),
                this._onAfirmaError.bind(this)
            );
        }
        return await this._super(...arguments);
    },
    _onAfirmaSign(afirma_value, afirma_certificate) {
        this.onSignatureProcess = false;
        this._onClickSign({
            skipAfirma: true,
            extra: {
                afirma_value,
                afirma_certificate,
                afirma_items: this._getAfirmaSignedData(),
            },
        });
    },
    _getAfirmaSignedData() {
        return JSON.stringify(this.info.items);
    },
    _onAfirmaError() {
        console.log("Something happened when processing the signature");
        this.onSignatureProcess = false;
    },
});
