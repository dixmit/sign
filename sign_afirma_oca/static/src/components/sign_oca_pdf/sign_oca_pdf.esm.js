/** @odoo-module */

import {patch} from "@web/core/utils/patch";
import SignOcaPdf from "@sign_oca/components/sign_oca_pdf/sign_oca_pdf.esm";

patch(SignOcaPdf.prototype, "sign_afirma", {
    async signOca() {
        console.log("SIGN AFIRMA");
        console.log(this);
    },
});
