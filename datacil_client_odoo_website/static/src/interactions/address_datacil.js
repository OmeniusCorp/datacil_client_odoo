import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

/**
 * Autocompletes the address form from the cédula / RUC when the website option
 * is enabled (flag rendered as `data-datacil-autocomplete` on the input).
 * Only empty inputs are filled so the visitor keeps control of the data.
 */
export class DatacilAddressAutocomplete extends Interaction {
    static selector = ".o_customer_address_fill";
    dynamicContent = {
        'input[name="vat"]': { "t-on-change": this.onVatChange },
    };

    setup() {
        this.form = this.el.querySelector("form.address_autoformat") || this.el.querySelector("form");
        this.vatInput = this.el.querySelector('input[name="vat"]');
        this.mode = this.vatInput?.dataset.datacilAutocomplete || "";
        this.lastQuery = "";
    }

    async onVatChange() {
        if (!this.mode || !this.form) {
            return;
        }
        const identification = (this.vatInput.value || "").replace(/\D/g, "");
        if (![10, 13].includes(identification.length) || identification === this.lastQuery) {
            return;
        }
        this.lastQuery = identification;
        this._setStatus(_t("Looking up your data..."), "text-muted");
        this.vatInput.classList.add("o_datacil_loading");
        try {
            const res = await this.waitFor(rpc("/datacil/website/lookup", { identification }));
            if (!res.success) {
                this._setStatus(res.code === "invalid" ? res.message : "", "text-muted");
                return;
            }
            this._fill(res.values || {});
            this._setStatus(_t("Data filled from your identification. Please review it."), "text-success");
        } catch {
            this._setStatus("", "");
        } finally {
            this.vatInput.classList.remove("o_datacil_loading");
        }
    }

    _fill(values) {
        for (const name of ["name", "company_name", "street", "street2", "city", "zip", "phone", "email"]) {
            const input = this.form.elements[name];
            if (input && values[name] && !input.value) {
                input.value = values[name];
            }
        }
        if (values.country_id) {
            const country = this.form.elements["country_id"];
            if (country && String(country.value) !== String(values.country_id)) {
                country.value = String(values.country_id);
                country.dispatchEvent(new Event("change", { bubbles: true }));
            }
        }
        if (values.state_id) {
            const state = this.form.elements["state_id"];
            if (state && !state.value) {
                // The state list may be reloaded after the country change above.
                const apply = () => {
                    const option = Array.from(state.options).find((o) => String(o.value) === String(values.state_id));
                    if (option) {
                        state.value = option.value;
                        state.dispatchEvent(new Event("change", { bubbles: true }));
                    }
                };
                apply();
                this.waitForTimeout(apply, 800);
            }
        }
    }

    _setStatus(message, cls) {
        let status = this.el.querySelector(".o_datacil_status");
        if (!status) {
            status = document.createElement("small");
            status.className = "o_datacil_status form-text d-block";
            this.vatInput.insertAdjacentElement("afterend", status);
        }
        status.textContent = message;
        status.className = `o_datacil_status form-text d-block ${cls}`;
    }
}

registry.category("public.interactions").add("datacil_client_odoo_website.address_autocomplete", DatacilAddressAutocomplete);
