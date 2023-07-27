odoo.define("sign_oca.textElement", function (require) {
    "use strict";
    const core = require("web.core");
    const SignRegistry = require("sign_oca.SignRegistry");
    const textSignOca = {
        generate: function (parent, item, signatureItem) {
            var input = $(
                core.qweb.render("sign_oca.sign_iframe_field_text", {item: item})
            )[0];
            signatureItem[0].addEventListener("focus_signature", () => {
                input.focus();
            });
            input.addEventListener("focus", (ev) => {
                if (
                    item.default_value &&
                    !item.value_text &&
                    parent.info.partner[item.default_value]
                ) {
                    ev.target.value = parent.info.partner[item.default_value];
                }
            });
            input.addEventListener("change", (ev) => {
                parent.env.services.rpc({
                    model: parent.props.model,
                    method: "write",
                    args: [
                        [parent.props.res_id],
                        {item_ids: [[1, item.id, {value_text: ev.srcElement.value}]]},
                    ],
                });
                item.value_text = ev.srcElement.value;
                parent.checkFilledAll();
            });
            input.addEventListener("keydown", (ev) => {
                if ((ev.keyCode || ev.which) !== 9) {
                    return true;
                }
                ev.preventDefault();
                var next_items = _.filter(
                    parent.info.items,
                    (i) => i.tabindex > item.tabindex
                ).sort((a, b) => a.tabindex - b.tabindex);
                if (next_items.length > 0) {
                    ev.currentTarget.blur();
                    parent.items[next_items[0].id].dispatchEvent(
                        new Event("focus_signature")
                    );
                }
            });
            return input;
        },
        check: function (item) {
            return Boolean(item.value_text);
        },
    };
    SignRegistry.add("text", textSignOca);
    return textSignOca;
});
