/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, xml } from "@odoo/owl";

// TaskProgressWidget
class TaskProgressWidget extends Component {
    static template = xml`
        <div class="o_task_progress_widget">
            <div class="progress" style="height: 20px;">
                <div t-attf-class="progress-bar bg-{{this.progressColor}}" 
                     role="progressbar" 
                     t-att-style="'width: ' + this.props.value + '%'" 
                     t-att-aria-valuenow="this.props.value" 
                     aria-valuemin="0" 
                     aria-valuemax="100">
                    <t t-esc="this.props.value"/>%
                </div>
            </div>
            <input type="range" class="form-range mt-2" 
                   t-on-change="(ev) => this.onChange(ev)" 
                   min="0" max="100" step="5" 
                   t-att-value="this.props.value"/>
        </div>
    `;

    static props = {
        ...standardFieldProps,
    };

    get progressColor() {
        const progress = this.props.value || 0;
        if (progress < 30) return 'danger';
        if (progress < 70) return 'warning';
        return 'success';
    }

    onChange(ev) {
        const newValue = parseInt(ev.target.value, 10);
        this.props.update(newValue);
    }
}

export const taskProgressField = {
    component: TaskProgressWidget,
    fieldDependencies: [],
};

registry.category("fields").add("task_progress", taskProgressField);