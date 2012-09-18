#-*- coding:utf-8 -*-
from pyramid.response import Response
from pyramid_handlers import action
from pyramid.renderers import render_to_response
from pyramid.httpexceptions import HTTPFound
from pyramid.url import route_url as url

from blog.libs.paginates import Page
from blog.libs.forms import FieldSet, Grid
from blog.models import Session
from blog import globals as g

from urllib2 import urlopen, Request
import json

class BaseHandler(object):
    def __init__(self, request):
        g.request = request
        self.request = request
        self.__before__()

        self.urlLogin = '/users/login?back_to='+self.request.path_url

    def __before__(self):
        pass

    def auth(self):
        session = self.request.session
        return 'user_id' not in session

    def get_id(self):
        if 'id' in self.request.matchdict:
            return self.request.matchdict['id']
        else:
            params = self.request.matchdict.get('params')
            if params:
                return params[0]
        return None

    def render(self, renderer, params={}):
        if isinstance(params, dict):
            return render_to_response(renderer, params, request=self.request)
        return params

class CrudHandler(BaseHandler):
    model = None # e.g. User
    url_base = None # e.g. 'user'
    renderer_base = None# e.g. '/derived/users'
    order_by = 'id'
    auth_actions = ['index', 'create', 'update', 'delete']

    def _do_index(self):
        page = self.request.GET.get('page', 1)
        query = Session.query(self.model).order_by(self.order_by).all()
        items = Page(query, page=page, items_per_page=10)

        grid = Grid(self.model, items)
        self.model._configure_grid(grid)
        
        return dict(grid=grid, items=items, url_base=self.url_base)

    def _do_create(self):
        form = FieldSet(self.model, data=self.request.params or None)
        self.model._configure_form(form)
        if self.request.params:
            if form.validate():
                form.sync()
                self.model._before_create(form, self.request.params)
                Session.add(form.model)
                self.request.session.flash(u'Item successfully added.', 'success')
                return HTTPFound(location=g.url(self.url_base))
            else:
                self.request.session.flash(u'Invalid data.', 'error')

        return dict(form=form, url_base=self.url_base)

    def _do_update(self):
        item = Session.query(self.model).get(self.get_id())
        
        form = FieldSet(item, data=self.request.params or None)
        self.model._configure_form(form)
        if self.request.params:
            if form.validate():
                form.sync()
                self.model._before_update(item, form, self.request.params)
                Session.add(form.model)
                self.request.session.flash(u'Item successfully updated.', 'success')
                return HTTPFound(location=g.url(self.url_base))
            else:
                self.request.session.flash(u'Invalid data', 'error')

        return dict(form=form, url_base=self.url_base)

    def _do_delete(self):
        item = Session.query(self.model).get(self.get_id())
        Session.delete(item)
        self.request.session.flash(u'Item deleted successfully.', 'success')
        return HTTPFound(location=g.url(self.url_base))


    def index(self):
        if 'index' in self.auth_actions and self.auth():
            return HTTPFound(location=self.urlLogin)

        params = self._do_index()
        if self.renderer_base:
            renderer = self.renderer_base+'/index.jinja2'
        else:
            renderer = '/bases/crud_index.jinja2'
        return self.render(renderer, params)

    def create(self):
        if 'create' in self.auth_actions and self.auth():
            return HTTPFound(location=self.urlLogin)

        params = self._do_create()
        if self.renderer_base:
            renderer = self.renderer_base+'/edit.jinja2'
        else:
            renderer = '/bases/crud_edit.jinja2'
        return self.render(renderer, params)

    def update(self):
        if 'update' in self.auth_actions and self.auth():
            return HTTPFound(location=self.urlLogin)

        params = self._do_update()
        if self.renderer_base:
            renderer = self.renderer_base+'/edit.jinja2'
        else:
            renderer = '/bases/crud_edit.jinja2'
        return self.render(renderer, params)

    def delete(self):
        if 'delete' in self.auth_actions and self.auth():
            return HTTPFound(location=self.urlLogin)

        return self._do_delete()
