/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

import { useDatacilLookup } from "@datacil_client_odoo/core/datacil_lookup_hook";

/**
 * `<widget name="datacil_lookup" field="vat" method="datacil_lookup"/>`
 *
 * A button that queries Datacil with the value of `field` and applies the
 * returned values on the current record (no save required, works on new
 * records). Attributes:
 *  - field:  field holding the identification / plate (default "vat")
 *  - method: python record method to call (default "datacil_lookup")
 *  - string: button label (default: "Validate")
 *  - icon:   font awesome icon (default "fa-search")
 *  - apply:  "0" to only display the result (default "1")
 *  - require_saved: "1" to disable the button on unsaved records
 *  - variant: "primary" (default), "secondary" or "link"
 */
export class DatacilLookupWidget extends Component {
    static template = "datacil_client_odoo.DatacilLookupWidget";
    static props = {
        ...standardWidgetProps,
        field: { type: String, optional: true },
        method: { type: String, optional: true },
        string: { type: String, optional: true },
        icon: { type: String, optional: true },
        apply: { type: Boolean, optional: true },
        requireSaved: { type: Boolean, optional: true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        field: "vat",
        method: "datacil_lookup",
        icon: "fa-search",
        apply: true,
        requireSaved: false,
        variant: "primary",
    };

    setup() {
        this.lookup = useDatacilLookup();
        this.state = useState({ loading: false });
    }

    get btnClass() {
        return this.props.variant === "link" ? "btn-link px-1" : `btn-${this.props.variant}`;
    }

    get label() {
        return this.props.string || _t("Validate");
    }

    get query() {
        const value = this.props.record.data[this.props.field];
        return typeof value === "string" ? value.trim() : "";
    }

    get isDisabled() {
        return (
            this.state.loading ||
            !this.query ||
            (this.props.requireSaved && !this.props.record.resId)
        );
    }

    get title() {
        if (!this.query) {
            return _t("Enter a value first");
        }
        if (this.props.requireSaved && !this.props.record.resId) {
            return _t("Save the record first");
        }
        return this.label;
    }

    async onClick() {
        if (this.isDisabled) {
            return;
        }
        this.state.loading = true;
        try {
            await this.lookup.run({
                record: this.props.record,
                method: this.props.method,
                query: this.query,
                apply: this.props.apply,
            });
        } finally {
            this.state.loading = false;
        }
    }
}

export const datacilLookupWidget = {
    component: DatacilLookupWidget,
    // Inline wrapper so the button sits next to the field it queries.
    additionalClasses: ["d-inline-block", "align-middle"],
    extractProps: ({ attrs }) => ({
        field: attrs.field || "vat",
        method: attrs.method || "datacil_lookup",
        string: attrs.string,
        icon: attrs.icon || "fa-search",
        apply: !["0", "false", "False"].includes(attrs.apply),
        requireSaved: ["1", "true", "True"].includes(attrs.require_saved),
        variant: ["primary", "secondary", "link"].includes(attrs.variant) ? attrs.variant : "primary",
    }),
};

registry.category("view_widgets").add("datacil_lookup", datacilLookupWidget);
