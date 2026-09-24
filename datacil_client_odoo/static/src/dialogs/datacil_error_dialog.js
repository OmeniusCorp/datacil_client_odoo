/** @odoo-module **/
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

/**
 * One screen per failure code returned by `datacil.api`:
 *  - not_configured / unauthorized: message + where to configure it (no action:
 *    the form may be unsaved, so navigating away would be blocked anyway)
 *  - no_credits: link to the credits dashboard
 *  - unavailable / rate_limit / error: retry button
 *  - invalid / not_found: plain message
 *  - already_exists: open the existing contact
 */
export class DatacilErrorDialog extends Component {
    static template = "datacil_client_odoo.DatacilErrorDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        result: Object,
        onRetry: { type: Function, optional: true },
    };

    setup() {
        this.action = useService("action");
        // Settings require the "Administration / Settings" group.
        this.isAdmin = user.isSystem;
    }

    get code() {
        return this.props.result.code || "error";
    }

    get screen() {
        const screens = {
            not_configured: {
                title: _t("Datacil is not configured"),
                icon: "fa-plug",
                cls: "text-warning",
                hint: this.isAdmin
                    ? _t("Configure it in Settings › Datacil (API URL and key), then come back and validate again.")
                    : _t("Ask your administrator to configure the Datacil connection in Settings › Datacil."),
            },
            unauthorized: {
                title: _t("Datacil API key rejected"),
                icon: "fa-key",
                cls: "text-danger",
                hint: this.isAdmin
                    ? _t("Check the API key in Settings › Datacil and try again.")
                    : _t("Ask your administrator to check the Datacil API key in Settings › Datacil."),
            },
            no_credits: {
                title: _t("No Datacil credits left"),
                icon: "fa-battery-empty",
                cls: "text-danger",
                hint: _t("Top up your Datacil balance to keep querying. No credits were consumed."),
            },
            unavailable: {
                title: _t("Datacil service unavailable"),
                icon: "fa-cloud",
                cls: "text-danger",
                hint: _t("The service did not answer. It usually recovers in a few minutes; no credits were consumed."),
            },
            rate_limit: {
                title: _t("Too many queries"),
                icon: "fa-hourglass-half",
                cls: "text-warning",
                hint: _t("Wait a moment before trying again."),
            },
            invalid: {
                title: _t("Invalid identification"),
                icon: "fa-times-circle",
                cls: "text-warning",
                hint: "",
            },
            not_found: {
                title: _t("No information found"),
                icon: "fa-search",
                cls: "text-muted",
                hint: "",
            },
            already_exists: {
                title: _t("Contact already registered"),
                icon: "fa-user",
                cls: "text-warning",
                hint: "",
            },
            forbidden: {
                title: _t("Service not allowed"),
                icon: "fa-ban",
                cls: "text-danger",
                hint: "",
            },
        };
        return (
            screens[this.code] || {
                title: _t("Datacil error"),
                icon: "fa-exclamation-triangle",
                cls: "text-danger",
                hint: "",
            }
        );
    }

    get canOpenDashboard() {
        return this.code === "no_credits";
    }

    get canRetry() {
        return !!this.props.onRetry && ["unavailable", "rate_limit", "error"].includes(this.code);
    }

    get existingPartner() {
        return this.props.result.existing_partner || null;
    }

    openDashboard() {
        this.props.close();
        this.action.doAction("datacil_client_odoo.action_datacil_dashboard");
    }

    openExisting() {
        this.props.close();
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: this.existingPartner.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    retry() {
        this.props.close();
        this.props.onRetry();
    }
}
