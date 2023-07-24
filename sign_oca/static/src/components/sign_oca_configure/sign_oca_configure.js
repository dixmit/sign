odoo.define(
    "sign_oca/static/src/components/sign_oca_configure/sign_oca_configure.js",
    function (require) {
        "use strict";

        const {ComponentWrapper} = require("web.OwlCompatibility");
        const AbstractAction = require("web.AbstractAction");
        const Dialog = require("web.Dialog");
        const core = require("web.core");
        const SignOcaPdfCommon = require("sign_oca/static/src/components/sign_oca_pdf_common/sign_oca_pdf_common.js");
        const _t = core._t;
        class SignOcaConfigure extends SignOcaPdfCommon {
            constructor() {
                super(...arguments);
                this.field_template = "sign_oca.sign_iframe_field_configure";
                this.contextMenu = undefined;
            }
            postIframeFields() {
                super.postIframeFields(...arguments);
                _.each(
                    this.iframe.el.contentDocument.getElementsByClassName("textLayer"),
                    (textLayer) => {
                        var page = textLayer.parentElement;
                        textLayer.addEventListener("contextmenu", (e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            if (this.contextMenu !== undefined) {
                                this.contextMenu.remove();
                                this.contextMenu = undefined;
                            }
                            var position = page.getBoundingClientRect();
                            this.contextMenu = $(
                                core.qweb.render("sign_oca.sign_iframe_contextmenu", {
                                    page,
                                    e,
                                    left:
                                        ((e.pageX - position.x) * 100) /
                                            position.width +
                                        "%",
                                    top:
                                        ((e.pageY - position.y) * 100) /
                                            position.height +
                                        "%",
                                    info: this.info,
                                    page_id: parseInt(page.dataset.pageNumber, 10),
                                })
                            );
                            page.append(this.contextMenu[0]);
                        });
                    }
                );
                this.iframe.el.contentDocument.addEventListener(
                    "click",
                    (ev) => {
                        if (!this.contextMenu && !this.creatingItem) {
                            if (!this.contextMenu[0].contains(ev.target)) {
                                this.contextMenu.remove();
                                this.contextMenu = undefined;
                            } else {
                                this.creatingItem = true;
                                this.env.services
                                    .rpc({
                                        model: this.props.model,
                                        method: "add_item",
                                        args: [
                                            [this.props.res_id],
                                            {
                                                field_id: parseInt(
                                                    ev.target.dataset.field,
                                                    10
                                                ),
                                                page: parseInt(
                                                    ev.target.dataset.page,
                                                    10
                                                ),
                                                position_x: parseFloat(
                                                    ev.target.parentElement.style.left
                                                ),
                                                position_y: parseFloat(
                                                    ev.target.parentElement.style.top
                                                ),
                                                width: 20,
                                                height: 1.5,
                                            },
                                        ],
                                    })
                                    .then((data) => {
                                        this.info.items[data.id] = data;
                                        this.postIframeField(data);
                                        this.contextMenu.remove();
                                        this.contextMenu = undefined;
                                        this.creatingItem = false;
                                    });
                            }
                        }
                    },
                    // We need to enforce it to happen no matter what
                    true
                );
                this.iframeLoaded.resolve();
            }
            postIframeField(item) {
                var signatureItem = super.postIframeField(...arguments);
                var dragItem = signatureItem[0].getElementsByClassName(
                    "o_sign_oca_draggable"
                )[0];
                var resizeItems = signatureItem[0].getElementsByClassName(
                    "o_sign_oca_resize"
                );
                signatureItem[0].addEventListener(
                    "click",
                    (e) => {
                        var target = e.currentTarget;
                        // TODO: Open Dialog for configuration
                        var dialog = new Dialog(this, {
                            title: _t("Edit field"),
                            $content: $(
                                core.qweb.render("sign_oca.sign_oca_field_edition", {
                                    item,
                                    info: this.info,
                                })
                            ),

                            buttons: [
                                {
                                    text: _t("Save"),
                                    classes: "btn-primary",
                                    close: true,
                                    click: () => {
                                        var field_id = parseInt(
                                            dialog.$el
                                                .find('select[name="field_id"]')
                                                .val(),
                                            10
                                        );
                                        var role_id = parseInt(
                                            dialog.$el
                                                .find('select[name="role_id"]')
                                                .val(),
                                            10
                                        );
                                        this.env.services
                                            .rpc({
                                                model: this.props.model,
                                                method: "set_item_data",
                                                args: [
                                                    [this.props.res_id],
                                                    item.id,
                                                    {
                                                        field_id,
                                                        role_id,
                                                    },
                                                ],
                                            })
                                            .then(() => {
                                                item.field_id = field_id;
                                                item.name = _.filter(
                                                    this.info.fields,
                                                    (field) => field.id === field_id
                                                )[0].name;
                                                item.role_id = role_id;
                                                target.remove();
                                                this.postIframeField(item);
                                            });
                                    },
                                },
                                {
                                    text: _t("Delete"),
                                    classes: "btn-danger",
                                    close: true,
                                    click: () => {
                                        this.env.services
                                            .rpc({
                                                model: this.props.model,
                                                method: "delete_item",
                                                args: [[this.props.res_id], item.id],
                                            })
                                            .then(() => {
                                                delete this.info.items[item.id];
                                                target.remove();
                                            });
                                    },
                                },
                                {
                                    text: _t("Cancel"),
                                    close: true,
                                },
                            ],
                        }).open();
                    },
                    true
                );
                dragItem.addEventListener(
                    "drag",
                    (e) => {
                        e.stopPropagation();
                        e.preventDefault();
                        var target = $(e.currentTarget).parent();
                        var position = target.parent()[0].getBoundingClientRect();
                        var left =
                            (Math.max(
                                0,
                                Math.min(position.width, e.pageX - position.x)
                            ) *
                                100) /
                            position.width;
                        var top =
                            (Math.max(
                                0,
                                Math.min(position.height, e.pageY - position.y)
                            ) *
                                100) /
                            position.height;
                        target.css("left", left + "%");
                        target.css("top", top + "%");
                    },
                    true
                );
                dragItem.addEventListener(
                    "dragend",
                    (e) => {
                        e.stopPropagation();
                        e.preventDefault();
                        var target = $(e.currentTarget).parent();
                        var position = target.parent()[0].getBoundingClientRect();
                        var left =
                            (Math.max(
                                0,
                                Math.min(position.width, e.pageX - position.x)
                            ) *
                                100) /
                            position.width;
                        var top =
                            (Math.max(
                                0,
                                Math.min(position.height, e.pageY - position.y)
                            ) *
                                100) /
                            position.height;
                        target.css("left", left + "%");
                        target.css("top", top + "%");
                        item.position_x = left;
                        item.position_y = top;
                        this.env.services.rpc({
                            model: this.props.model,
                            method: "set_item_data",
                            args: [
                                [this.props.res_id],
                                item.id,
                                {
                                    position_x: left,
                                    position_y: top,
                                },
                            ],
                        });
                    },
                    true
                );
                _.each(resizeItems, (resizeItem) => {
                    resizeItem.addEventListener("drag", (e) => {
                        e.stopPropagation();
                        e.preventDefault();
                        var target = $(e.currentTarget).parent();
                        var targetPosition = e.currentTarget.getBoundingClientRect();
                        var itemPosition = target[0].getBoundingClientRect();
                        var pagePosition = target.parent()[0].getBoundingClientRect();
                        var width =
                            (Math.max(
                                0,
                                e.pageX + targetPosition.width - itemPosition.x
                            ) *
                                100) /
                            pagePosition.width;
                        var height =
                            (Math.max(
                                0,
                                e.pageY + targetPosition.height - itemPosition.y
                            ) *
                                100) /
                            pagePosition.height;
                        target.css("width", width + "%");
                        target.css("height", height + "%");
                    });
                    resizeItem.addEventListener("dragend", (e) => {
                        e.stopPropagation();
                        e.preventDefault();
                        var target = $(e.currentTarget).parent();
                        var targetPosition = e.currentTarget.getBoundingClientRect();
                        var itemPosition = target[0].getBoundingClientRect();
                        var pagePosition = target.parent()[0].getBoundingClientRect();
                        var width =
                            (Math.max(
                                0,
                                e.pageX + targetPosition.width - itemPosition.x
                            ) *
                                100) /
                            pagePosition.width;
                        var height =
                            (Math.max(
                                0,
                                e.pageY + targetPosition.height - itemPosition.y
                            ) *
                                100) /
                            pagePosition.height;
                        target.css("width", width + "%");
                        target.css("height", height + "%");
                        item.width = width;
                        item.height = height;
                        this.env.services.rpc({
                            model: this.props.model,
                            method: "set_item_data",
                            args: [
                                [this.props.res_id],
                                item.id,
                                {
                                    width: width,
                                    height: height,
                                },
                            ],
                        });
                    });
                });
                return signatureItem;
                /* Var component = new SignOcaPdfField(this, {...item});
                console.log(this.iframe.el.contentDocument.getElementsByClassName('page')[item.page - 1].__proto__)
                component.mount(this.iframe.el.contentDocument.getElementsByClassName('page')[item.page - 1])*/
            }
        }
        const SignOcaConfigureAction = AbstractAction.extend({
            hasControlPanel: true,
            init: function (parent, action) {
                this._super.apply(this, arguments);
                this.model =
                    (action.params.res_model !== undefined &&
                        action.params.res_model) ||
                    action.context.params.res_model;
                this.res_id =
                    (action.params.res_id !== undefined && action.params.res_id) ||
                    action.context.params.id;
            },
            async start() {
                await this._super(...arguments);
                this.component = new ComponentWrapper(this, SignOcaConfigure, {
                    model: this.model,
                    res_id: this.res_id,
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
        core.action_registry.add("sign_oca_configure", SignOcaConfigureAction);

        return {
            SignOcaConfigure,
            SignOcaConfigureAction,
        };
    }
);