import unittest

import httplib2
import mox

from remoteobjects import fields, http, promise
from tests import test_dataobject, test_http
from tests import utils


class TestDataObjects(test_dataobject.TestDataObjects):

    cls = promise.PromiseObject


class TestHttpObjects(test_http.TestHttpObjects):

    cls = promise.PromiseObject


class TestPromiseObjects(unittest.TestCase):

    cls = promise.PromiseObject

    def test_basic(self):

        class Tiny(self.cls):
            name = fields.Field()

        h = mox.MockObject(httplib2.Http)
        mox.Replay(h)

        url = 'http://example.com/whahay'
        t = Tiny.get(url, http=h)

        # Check that we didn't do anything.
        mox.Verify(h)

        headers = {"accept": "application/json"}
        request = dict(uri=url, headers=headers)
        content = """{"name": "Mollifred"}"""
        h = utils.mock_http(request, content)
        t._http = h  # inject, oops
        self.assertEquals(t.name, 'Mollifred')
        mox.Verify(h)

    def test_filter(self):

        class Toy(self.cls):
            name = fields.Field()

        h = mox.MockObject(httplib2.Http)
        mox.Replay(h)

        b = Toy.get('http://example.com/foo', http=h)
        self.assertEquals(b._location, 'http://example.com/foo')

        x = b.filter(limit=10, offset=7)
        self.assert_(x is not b)
        self.assertEquals(b._location, 'http://example.com/foo')
        self.assertEquals(x._location, 'http://example.com/foo?limit=10&offset=7')

        y = b.filter(awesome='yes')
        self.assertEquals(y._location, 'http://example.com/foo?awesome=yes')
        y = y.filter(awesome='no')
        self.assertEquals(y._location, 'http://example.com/foo?awesome=no')

        # Nobody did any HTTP, right?
        mox.Verify(h)

    def test_awesome(self):

        class Toy(self.cls):
            name = fields.Field()

        class Room(self.cls):
            toybox = fields.Link(Toy)

        r = Room.get('http://example.com/bwuh/')
        b = r.toybox
        self.assert_(isinstance(b, Toy))
        self.assertEquals(b._location, 'http://example.com/bwuh/toybox')

    def test_set_before_delivery(self):

        class Toy(self.cls):
            names = fields.List(fields.Field())
            foo = fields.Field()

        url = 'http://example.com/whahay'
        headers = {"accept": "application/json"}
        request = dict(uri=url, headers=headers)
        content = """{"names": ["Mollifred"], "foo":"something"}"""
        h = utils.mock_http(request, content)

        # test case where attribute is assigned to object ahead of delivery
        t = Toy.get(url, http=h)
        t.names = ["New name"]
        d = t.to_dict() # this delivers the object

        # self.assertEquals(t.foo, "something")
        self.assertEquals(d['names'][0], "New name")
        self.assertEquals(t.names[0], "New name")

        h = utils.mock_http(request, content)
        # test case where we update_from_dict explictly after setting attributes
        t = Toy.get(url, http=h)
        t.foo = "local change"
        t.update_from_dict({"names": ["local update"]})

        self.assertEquals(t.foo, None)
