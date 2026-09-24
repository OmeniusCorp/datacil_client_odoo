/** @odoo-module **/
import { Component, markup } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * Shows what Datacil returned (summary rows and/or HTML) and lets the user
 * apply the values on the form.
 */
export class DatacilResultDialog extends Component {
    static template = "datacil_client_odoo.DatacilResultDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        result: Object,
        canApply: { type: Boolean, optional: true },
        onApply: { type: Function, optional: true },
    };
    static defaultProps = { canApply: false };

    setup() {
        this.action = useService("action");
    }

    get title() {
        return this.props.result.title || _t("Datacil: information found");
    }

    get rows() {
        return this.props.result.rows || [];
    }

    get credits() {
        return this.props.result.credits || null;
    }

    get html() {
        // Built server side with Markup (values escaped), safe to inject.
        return this.props.result.html ? markup(this.props.result.html) : null;
    }

    async onApply() {
        if (this.props.onApply) {
            await this.props.onApply();
        }
        this.props.close();
    }

    openExisting() {
        const partner = this.props.result.existing_partner;
        this.props.close();
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partner.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}
