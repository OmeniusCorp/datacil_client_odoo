/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

class DatacilDashboard extends Component {
    static template = "datacil_client_odoo.datacil_dashboard";
    static props = ["*"];

    setup() {
        this.notification = useService("notification");
        this.action = useService("action");
        this.isSystem = user.isSystem;
        this.state = useState({
            credits: null,
            history: [],
            costs: [],
            loading: true,
            error: null,
            errorCode: null,
        });

        onWillStart(() => this.loadData());
    }

    async loadData(force = false) {
        this.state.loading = true;
        this.state.error = null;
        this.state.errorCode = null;
        try {
            // One round trip: credits (cached server side), history and costs.
            const res = await rpc("/datacil/dashboard", { force });
            if (!res.success) {
                this.state.error = res.message;
                this.state.errorCode = res.code;
                return;
            }
            this.state.credits = res.credits;
            this.state.history = (res.history || []).map((t) => ({
                ...t,
                date: this._formatDate(t.$createdAt || t.createdAt || t.date),
            }));
            this.state.costs = res.costs || [];
            if (res.history_error) {
                this.notification.add(res.history_error, { type: "warning" });
            }
        } catch {
            this.state.error = _t("Could not connect to the service.");
            this.state.errorCode = "unavailable";
        } finally {
            this.state.loading = false;
        }
    }

    async onRefresh() {
        await this.loadData(true);
        if (!this.state.error) {
            this.notification.add(_t("Dashboard updated"), { type: "success" });
        }
    }

    openSettings() {
        this.action.doAction("datacil_client_odoo.action_datacil_config_settings");
    }

    _formatDate(isoString) {
        if (!isoString) {
            return "";
        }
        const d = new Date(isoString);
        return d.toLocaleString(user.lang?.replace("_", "-") || "es-EC", {
            year: "numeric",
            month: "short",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    get totalSpent() {
        return this.state.history.reduce((sum, t) => sum + Math.abs(t.amount || 0), 0);
    }

    get serviceBreakdown() {
        const map = {};
        for (const t of this.state.history) {
            const key = t.service_key || t.serviceKey || "unknown";
            if (!map[key]) {
                map[key] = { service: key, count: 0, total: 0 };
            }
            map[key].count++;
            map[key].total += Math.abs(t.amount || 0);
        }
        return Object.values(map);
    }
}

registry.category("actions").add("datacil_client_odoo.datacil_dashboard", DatacilDashboard);
