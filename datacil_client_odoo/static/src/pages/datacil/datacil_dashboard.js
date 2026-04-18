/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class DatacilDashboard extends Component {
    static template = "datacil_client_odoo.datacil_dashboard";

    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc")
        this.state = useState({
            credits: null,
            history: [],
            costs: [],
            loading: true,
            error: null,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const [creditsRes, historyRes, costsRes] = await Promise.all([
                this.rpc("/datacil/credits", {}),
                this.rpc("/datacil/credits/history", {}),
                this.rpc("/datacil/costs", {}),
            ]);

            if (!creditsRes.success) {
                this.state.error = creditsRes.message;
                return;
            }

            this.state.credits = creditsRes.data;
            this.state.history = (historyRes.data?.transactions || []).map((t) => ({
                ...t,
                date: this._formatDate(t.$createdAt),
            }));
            this.state.costs = costsRes.data?.costs || [];
        } catch (e) {
            this.state.error = _t("Could not connect to the service.");
        } finally {
            this.state.loading = false;
        }
    }

    async onRefresh() {
        await this.loadData();
        this.notification.add(_t("Dashboard updated"), { type: "success" });
    }

    _formatDate(isoString) {
        if (!isoString) return "";
        const d = new Date(isoString);
        return d.toLocaleString("es-EC", {
            year: "numeric",
            month: "short",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    get totalSpent() {
        return this.state.history.reduce((sum, t) => sum + Math.abs(t.amount), 0);
    }

    get serviceBreakdown() {
        const map = {};
        for (const t of this.state.history) {
            const key = t.service_key || "unknown";
            if (!map[key]) {
                map[key] = { service: key, count: 0, total: 0 };
            }
            map[key].count++;
            map[key].total += Math.abs(t.amount);
        }
        return Object.values(map);
    }
}

registry.category("actions").add("datacil_client_odoo.datacil_dashboard", DatacilDashboard);
