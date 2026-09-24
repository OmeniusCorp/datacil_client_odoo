/** @odoo-module **/
import { browser } from "@web/core/browser/browser";
import { deserializeDate, deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { onWillUnmount } from "@odoo/owl";

import { DatacilErrorDialog } from "@datacil_client_odoo/dialogs/datacil_error_dialog";
import { DatacilResultDialog } from "@datacil_client_odoo/dialogs/datacil_result_dialog";

// Seconds after which the blocking message tells the user the query is slow.
const SLOW_REQUEST_DELAY = 8;

/**
 * Shared behaviour for every "query Datacil" button in the backend.
 *
 * `run()` blocks the UI with an explicit message, calls `method` on the
 * record's model and then opens either the result dialog (with an "Apply"
 * button feeding `record.update`) or the error dialog matching the result
 * code (`not_configured`, `no_credits`, `unavailable`, ...).
 *
 * The python method must be a record method accepting the query as first
 * argument and returning the dict built by `datacil.api._result()`.
 */
export function useDatacilLookup() {
    const orm = useService("orm");
    const ui = useService("ui");
    const dialog = useService("dialog");
    let slowTimer = null;

    function clearSlowTimer() {
        if (slowTimer) {
            browser.clearTimeout(slowTimer);
            slowTimer = null;
        }
    }
    onWillUnmount(clearSlowTimer);

    function block(query) {
        const suffix = query ? ` (${query})` : "";
        ui.block({ message: _t("Querying Datacil, please wait...") + suffix });
        slowTimer = browser.setTimeout(() => {
            // Swap the message: both events are handled synchronously and OWL
            // batches the render, so there is no flicker.
            ui.unblock();
            ui.block({
                message:
                    _t("The query is taking longer than usual, still waiting for Datacil...") + suffix,
            });
        }, SLOW_REQUEST_DELAY * 1000);
    }

    function unblock() {
        clearSlowTimer();
        ui.unblock();
    }

    /**
     * @param {Object} params
     * @param {import("@web/model/relational_model/record").Record} params.record
     * @param {string} params.method python record method to call
     * @param {string} params.query identification / plate / ... sent to the method
     * @param {boolean} [params.apply=true] offer to apply `result.values` on the record
     * @param {Function} [params.onApplied] called after values were applied
     * @returns {Promise<Object>} the python result
     */
    async function run({ record, method, query, apply = true, onApplied }) {
        const model = record.resModel;
        const ids = record.resId ? [record.resId] : [];
        if (!apply && record.resId && (await record.isDirty())) {
            // Server-side flows reload the record afterwards: keep pending edits.
            const saved = await record.save();
            if (!saved) {
                return null;
            }
        }
        let result;
        block(query);
        try {
            result = await orm.call(model, method, [ids, query], { context: record.context });
        } finally {
            unblock();
        }

        if (!result || !result.success) {
            dialog.add(DatacilErrorDialog, {
                result: result || { code: "error", message: _t("Unexpected error while querying Datacil.") },
                onRetry: () => run({ record, method, query, apply, onApplied }),
            });
            return result;
        }

        // Only fields known by the current view can be updated client side, and
        // date/datetime values must be luxon objects (the server sends strings).
        const values = {};
        for (const [name, value] of Object.entries(result.values || {})) {
            const field = record.fields[name];
            if (!field) {
                continue;
            }
            if (value && field.type === "datetime" && typeof value === "string") {
                values[name] = deserializeDateTime(value);
            } else if (value && field.type === "date" && typeof value === "string") {
                values[name] = deserializeDate(value);
            } else {
                values[name] = value;
            }
        }
        // Flows that write server side (employees, documents, ...) refresh the
        // form right away, so the new data shows without reloading the page.
        if (result.reload && record.resId) {
            await record.load();
        }

        dialog.add(DatacilResultDialog, {
            result,
            canApply: apply && Object.keys(values).length > 0,
            onApply: async () => {
                if (Object.keys(values).length) {
                    // `name` first: some forms rely on it to enable the other fields.
                    if (values.name) {
                        await record.update({ name: values.name });
                    }
                    await record.update(values);
                }
                if (onApplied) {
                    await onApplied(result);
                }
            },
        });
        return result;
    }

    return { run };
}
