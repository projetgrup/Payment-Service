/** @odoo-module **/

import { actionService } from "@web/webclient/actions/action_service";

const actionStart = actionService.start;
actionService.start = async function start(env) {
    const res = actionStart(env);
    const services = env.services
    const router = services.router;
    const { cids, action, menu_id } = router.current.hash;
    if (services.user.context.system) {
        try {
            const state = await services.rpc("/web/system/load", { cids, action, menu_id });
            if (state.action) {
                router.current.hash.action = state.action;
            }
            if (state.menu_id) {
                router.current.hash.menu_id = state.menu_id;
            }
            router.pushState(state, { replace: true });
        } catch {}
    }
    return res;
}