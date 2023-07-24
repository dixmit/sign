odoo.define(
    "sign_oca/static/src/components/sign_oca_pdf_common/sign_oca_pdf_common.js",
    function (require) {
        "use strict";
        const {Component} = owl;
        const {onMounted, onWillStart, useRef} = owl.hooks;
        const Dialog = require("web.Dialog");
        const core = require("web.core");
        const _t = core._t;
        class SignOcaPdfCommon extends Component {
            constructor() {
                super(...arguments);
                this.field_template = "sign_oca.sign_iframe_field";
                this.pdf_url =
                    "/web/content/" +
                    this.props.model +
                    "/" +
                    this.props.res_id +
                    "/data";
                this.viewer_url =
                    "/web/static/lib/pdfjs/web/viewer.html?file=" + this.pdf_url;
                this.iframe = useRef("sign_oca_iframe");
                var iframeResolve = undefined;
                var iframeReject = undefined;
                this.iframeLoaded = new Promise(function (resolve, reject) {
                    iframeResolve = resolve;
                    iframeReject = reject;
                });
                this.items = {};

                this.iframeLoaded.resolve = iframeResolve;
                this.iframeLoaded.reject = iframeReject;
                onWillStart(this.willStart.bind(this));
                onMounted(() => {
                    this.waitIframeLoaded();
                });
            }
            async willStart() {
                this.info = await this.env.services.rpc({
                    model: this.props.model,
                    method: "get_info",
                    args: [[this.props.res_id]],
                });
            }
            waitIframeLoaded() {
                var error = this.iframe.el.contentDocument.getElementById(
                    "errorWrapper"
                );
                if (error && window.getComputedStyle(error).display !== "none") {
                    this.iframeLoaded.resolve();
                    return Dialog.alert(
                        this,
                        _t("Need a valid PDF to add signature fields !")
                    );
                }
                var nbPages = this.iframe.el.contentDocument.getElementsByClassName(
                    "page"
                ).length;
                var nbLayers = this.iframe.el.contentDocument.getElementsByClassName(
                    "textLayer"
                ).length;
                if (nbPages > 0 && nbLayers > 0 && nbPages === nbLayers) {
                    this.postIframeFields();
                } else {
                    var self = this;
                    setTimeout(function () {
                        self.waitIframeLoaded();
                    }, 50);
                }
            }
            postIframeFields() {
                this.iframe.el.contentDocument
                    .getElementById("viewerContainer")
                    .addEventListener(
                        "drop",
                        (e) => {
                            e.stopImmediatePropagation();
                            e.stopPropagation();
                        },
                        true
                    );
                var iframeCss = document.createElement("link");
                iframeCss.setAttribute("rel", "stylesheet");
                iframeCss.setAttribute("href", "/sign_oca/get_assets.css");

                var iframeJs = document.createElement("script");
                iframeJs.setAttribute("type", "text/javascript");
                iframeJs.setAttribute("src", "/sign_oca/get_assets.js");
                this.iframe.el.contentDocument
                    .getElementsByTagName("head")[0]
                    .append(iframeCss);
                this.iframe.el.contentDocument
                    .getElementsByTagName("head")[0]
                    .append(iframeJs);
                _.each(this.info.items, (item) => {
                    this.postIframeField(item);
                });
                this.iframeLoaded.resolve();
            }
            postIframeField(item) {
                var page = this.iframe.el.contentDocument.getElementsByClassName(
                    "page"
                )[item.page - 1];
                var signatureItem = $(
                    core.qweb.render(this.field_template, {
                        ...item,
                    })
                );
                page.append(signatureItem[0]);
                this.items[item.id] = signatureItem[0];
                return signatureItem;
            }
        }
        SignOcaPdfCommon.template = "sign_oca.SignOcaPdfCommon";

        return SignOcaPdfCommon;
    }
);
