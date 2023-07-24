odoo.define("sign_oca/static/src/components/sign_oca_pdf/sign_oca_pdf.js", function (
    require
) {
    "use strict";

    const {ComponentWrapper} = require("web.OwlCompatibility");
    const AbstractAction = require("web.AbstractAction");
    const core = require("web.core");
    const SignOcaPdfCommon = require("sign_oca/static/src/components/sign_oca_pdf_common/sign_oca_pdf_common.js");
    const SignRegistry = require("sign_oca.SignRegistry");
    class SignOcaPdf extends SignOcaPdfCommon {
        constructor() {
            super(...arguments);
            this.to_sign = false;
        }
        async willStart() {
            await super.willStart(...arguments);
            this.checkFilledAll();
        }
        checkToSign() {
            if (this.to_sign !== this.to_sign_update) {
                this.props.updateControlPanel({
                    cp_content: {
                        $buttons: this.renderButtons(this.to_sign_update),
                    },
                });
                this.to_sign = this.to_sign_update;
            }
        }
        renderButtons(to_sign) {
            var $buttons = $(
                core.qweb.render("oca_sign_oca.SignatureButtons", {
                    to_sign: to_sign,
                })
            );
            $buttons.on("click.o_sign_oca_button_sign", () => {
                this.env.services
                    .rpc({
                        model: this.props.model,
                        method: "action_sign",
                        args: [[this.props.res_id]],
                    })
                    .then(() => {
                        this.props.trigger("history_back");
                    });
            });
            return $buttons;
        }
        postIframeField(item) {
            var signatureItem = super.postIframeField(...arguments);
            signatureItem[0].append(
                SignRegistry.map[item.field_type].generate(this, item, signatureItem)
            );
            return signatureItem;
        }
        checkFilledAll() {
            this.to_sign_update =
                _.filter(this.info.items, (item) => {
                    return (
                        item.required && !SignRegistry.map[item.field_type].check(item)
                    );
                }).length === 0;
            this.checkToSign();
        }
    }
    const SignOcaPdfAction = AbstractAction.extend({
        hasControlPanel: true,
        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.model =
                (action.params.res_model !== undefined && action.params.res_model) ||
                action.context.params.res_model;
            this.res_id =
                (action.params.res_id !== undefined && action.params.res_id) ||
                action.context.params.id;
        },
        async start() {
            await this._super(...arguments);
            this.component = new ComponentWrapper(this, SignOcaPdf, {
                model: this.model,
                res_id: this.res_id,
                updateControlPanel: this.updateControlPanel.bind(this),
                trigger: this.trigger_up.bind(this),
            });
            return this.component.mount(this.$(".o_content")[0]);
        },
        getState: function () {
            var result = this._super(...arguments);
            result = _.extend({}, result, {
                res_model: this.model,
                res_id: this.res_id,
            });
            return result;
        },
    });
    core.action_registry.add("sign_oca", SignOcaPdfAction);

    return {
        SignOcaPdf,
        SignOcaPdfAction,
    };
});
