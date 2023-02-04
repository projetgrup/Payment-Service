/** @odoo-module **/

import ActionpadWidget from 'point_of_sale.ActionpadWidget';
import Registries from 'point_of_sale.Registries';

export const PosActionpadWidget = (ActionpadWidget) => 
    class PosActionpadWidget extends ActionpadWidget {
        get address() {
            return this.props.address;
        }
    };

Registries.Component.extend(ActionpadWidget, PosActionpadWidget);
