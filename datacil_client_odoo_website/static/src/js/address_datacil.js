/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

// Input names differ between the checkout (zip) and the portal account form (zipcode).
const FIELD_ALIASES = {
    name: ["name"],
    company_name: ["company_name"],
    street: ["street"],
    street2: ["street2"],
    city: ["city"],
    zip: ["zip", "zipcode"],
    phone: ["phone"],
    email: ["email"],
};

/**
 * Autocompletes the address form from the cédula / RUC when the website option
 * is enabled. The portal account form carries the option as
 * `data-datacil-autocomplete` on the input ("off" when disabled); the checkout
 * form has no flag, so the server decides (it answers "disabled" when off).
 * Only empty inputs are filled so the visitor keeps control of the data.
 */
publicWidget.registry.DatacilAddressAutocomplete = publicWidget.Widget.extend({
    selector: ".o_wsale_address_fill, .o_portal_details",
    events: {
        'change input[name="vat"]': "_onVatChange",
    },

    start() {
        this.form =
            this.el.querySelector("form.checkout_autoformat") ||
            this.el.closest("form") ||
            this.el.querySelector("form");
        this.vatInput = this.el.querySelector('input[name="vat"]');
        this.mode = this.vatInput?.dataset.datacilAutocomplete || "auto";
        this.lastQuery = "";
        this.timers = [];
        return this._super(...arguments);
    },

    destroy() {
        for (const timer of this.timers || []) {
            browser.clearTimeout(timer);
        }
        this._super(...arguments);
    },

    async _onVatChange() {
        if (this.mode === "off" || !this.form || !this.vatInput) {
            return;
        }
        const identification = (this.vatInput.value || "").replace(/\D/g, "");
        if (![10, 13].includes(identification.length) || identification === this.lastQuery) {
            return;
        }
        this.lastQuery = identification;
        // Without a flag the option may be off: stay silent until the server answers.
        const known = this.mode !== "auto";
        if (known) {
            this._setStatus(_t("Looking up your data..."), "text-muted");
        }
        this.vatInput.classList.add("o_datacil_loading");
        try {
            const res = await rpc("/datacil/website/lookup", { identification });
            if (!res.success) {
                if (res.code === "disabled") {
                    this.mode = "off";
                }
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
    },

    _input(name) {
        for (const alias of FIELD_ALIASES[name] || [name]) {
            const input = this.form.elements[alias];
            if (input) {
                return input;
            }
        }
        return null;
    },

    _fill(values) {
        for (const name of Object.keys(FIELD_ALIASES)) {
            const input = this._input(name);
            if (input && values[name] && !input.value && !input.readOnly && !input.disabled) {
                input.value = values[name];
            }
        }
        if (values.country_id) {
            const country = this.form.elements["country_id"];
            if (country && !country.disabled && String(country.value) !== String(values.country_id)) {
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
                    if (option && state.value !== option.value) {
                        state.value = option.value;
                        state.dispatchEvent(new Event("change", { bubbles: true }));
                    }
                };
                apply();
                // The checkout reloads the states after a 500 ms debounce plus an RPC.
                for (const delay of [800, 1600]) {
                    this.timers.push(browser.setTimeout(apply, delay));
                }
            }
        }
    },

    _setStatus(message, cls) {
        let status = this.el.querySelector(".o_datacil_status");
        if (!status) {
            if (!message) {
                return;
            }
            status = document.createElement("small");
            this.vatInput.insertAdjacentElement("afterend", status);
        }
        status.textContent = message;
        status.className = `o_datacil_status form-text d-block ${cls}`;
    },
});

export default publicWidget.registry.DatacilAddressAutocomplete;
