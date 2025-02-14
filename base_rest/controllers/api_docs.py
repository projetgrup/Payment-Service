# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import json
from contextlib import contextmanager

from odoo import _
from odoo.http import Controller, request, route
from odoo.addons.component.core import WorkContext

from ..core import _rest_services_databases
from .main import _PseudoCollection


class ApiDocsController(Controller):
    def make_json_response(self, data, headers=None, cookies=None):
        data = json.dumps(data, default=str)
        if headers is None:
            headers = {}
        headers["Content-Type"] = "application/json"
        return request.make_response(data, headers=headers, cookies=cookies)

    @route(
        ["/api", "/api/<collection>", "/api/index.html"],
        methods=["GET"],
        type="http",
        auth="public",
    )
    def index(self, collection=None, **params):
        urls = self._get_api_urls()
        system = getattr(request.env.company, 'system', False)
        if collection:
            urls = [url for url in urls if collection in url['name']]
        elif system:
            urls = [url for url in urls if system in url['name']]

        settings = {"urls": urls}
        return request.render("base_rest.openapi_redoc", {
            "settings": settings,
            "labels": json.dumps({
                "enum": _("Enum"),
                "enumSingleValue": _("Value"),
                "enumArray": _("Items"),
                "default": _("Default"),
                "deprecated": _("Deprecated"),
                "example": _("Example"),
                "examples": _("Examples"),
                "recursive": _("Recursive"),
                "arrayOf": _("Array of "),
                "webhook": _("Event"),
                "const": _("Value"),
                "noResultsFound": _("No results found"),
                "download": _("Download"),
                "downloadSpecification": _("Download OpenAPI specification"),
                "responses": _("Responses"),
                "callbackResponses": _("Callback responses"),
                "requestSamples": _("Request samples"),
                "responseSamples": _("Response samples"),
            })
        })

    @route(
        ["/api/s"],
        methods=["GET"],
        type="http",
        auth="public",
    )
    def index_swagger(self, **params):
        settings = {
            "urls": self._get_api_urls(),
            "service": params.get("service"),
        }
        return request.render("base_rest.openapi", {"settings": settings})

    @route("/api/<path:collection>/<string:service_name>.json", auth="public")
    def api(self, collection, service_name):
        with self.service_and_controller_class(collection, service_name) as (
            service,
            controller_class,
        ):
            openapi_doc = service.to_openapi(
                default_auth=controller_class._default_auth
            )
            return self.make_json_response(openapi_doc)

    def _get_api_urls(self):
        """
        This method lookup into the dictionary of registered REST service
        for the current database to built the list of available REST API
        :return:
        """
        services_registry = _rest_services_databases.get(request.env.cr.dbname, {})
        api_urls = []
        for rest_root_path, spec in list(services_registry.items()):
            collection_path = rest_root_path[1:-1]  # remove '/'
            collection_name = spec["collection_name"]
            for service in self._get_service_in_collection(collection_name):
                api_urls.append(
                    {
                        "name": "{}: {}".format(collection_path, service._usage),
                        "url": "/api/%s/%s.json"
                        % (collection_path, service._usage),
                    }
                )
        api_urls = sorted(api_urls, key=lambda k: k["name"])
        return api_urls

    def _filter_service_components(self, components):
        reg_model = request.env["rest.service.registration"]
        return [c for c in components if reg_model._filter_service_component(c)]

    def _get_service_in_collection(self, collection_name):
        with self.work_on_component(collection_name) as work:
            components = work.components_registry.lookup(collection_name)
            services = self._filter_service_components(components)
            services = [work.component(usage=s._usage) for s in services]
        return services

    @contextmanager
    def service_and_controller_class(self, collection_path, service_name):
        """
        Return the component that implements the methods of the requested
        service.
        :param collection_path:
        :param service_name:
        :return: an instance of invader.service component,
                 the base controller class serving the service
        """
        services_spec = self._get_services_specs(collection_path)
        collection_name = services_spec["collection_name"]
        controller_class = services_spec["controller_class"]
        with self.work_on_component(collection_name) as work:
            service = work.component(usage=service_name)
            yield service, controller_class

    @contextmanager
    def work_on_component(self, collection_name):
        """
        Return the all the components implementing REST services
        :param collection_name:
        :return: a WorkContext instance
        """

        collection = _PseudoCollection(collection_name, request.env)
        yield WorkContext(model_name="rest.service.registration", collection=collection)

    def _get_services_specs(self, path):
        services_registry = _rest_services_databases.get(request.env.cr.dbname, {})
        return services_registry["/" + path + "/"]
