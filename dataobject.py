import logging
import remoteobjects.fields

all_classes = {}
def find_by_name(name):
    """Finds and returns the DataObject subclass with the given name.

    Parameter `name` should be a bare class name with no module. If there is
    no class by that name, raises `KeyError`.

    """
    return all_classes[name]

class DataObjectMetaclass(type):
    """Metaclass for `DataObject` classes.

    This metaclass installs all `remoteobjects.fields.Property` instances
    declared as attributes of the new class, including all `Field` and `Link`
    instances.

    This metaclass also makes the new class findable through the
    `dataobject.find_by_name()` function.

    """

    def __new__(cls, name, bases, attrs):
        """Creates and returns a new `DataObject` class with its declared
        fields and name."""
        fields = {}
        new_fields = {}

        # Inherit all the parent DataObject classes' fields.
        for base in bases:
            if isinstance(base, DataObjectMetaclass):
                fields.update(base.fields)

        # Move all the class's attributes that are Fields to the fields set.
        for attrname, field in attrs.items():
            if isinstance(field, remoteobjects.fields.Property):
                new_fields[attrname] = field
                try:
                    repl = field.install(attrname)
                except NotImplementedError:
                    del attrs[attrname]
                else:
                    attrs[attrname] = repl
            elif attrname in fields:
                # Throw out any parent fields that the subclass defined as
                # something other than a Field.
                del fields[attrname]

        fields.update(new_fields)
        attrs['fields'] = fields
        obj_cls = super(DataObjectMetaclass, cls).__new__(cls, name, bases, attrs)

        # Register the new class so Object fields can have forward-referenced it.
        all_classes[name] = obj_cls

        # Tell this class's fields what this class is, so they can find their
        # forward references later.
        for field in new_fields.values():
            field.of_cls = obj_cls

        return obj_cls

class DataObject(object):

    """An object that can be decoded from or encoded as a dictionary.

    DataObject subclasses should be declared with their different data
    attributes defined as instances of fields from the `remoteobjects.fields`
    module. For example:

    >>> from remoteobjects import DataObject, fields
    >>> class Asset(DataObject):
    ...     name    = fields.Field()
    ...     updated = fields.Datetime()
    ...     author  = fields.Object('Author')
    ...

    A DataObject's fields then provide the coding between live DataObject
    instances and dictionaries.

    """

    __metaclass__ = DataObjectMetaclass

    def __init__(self, **kwargs):
        """Initializes a new `DataObject` with the given field values."""
        self.__dict__.update(kwargs)

    def __eq__(self, other):
        """Returns whether two `DataObject` instances are equivalent.

        If the `DataObject` instances are of the same type and contain the
        same data in all their fields, the objects are equivalent.

        """
        if type(self) != type(other):
            return False
        for k, v in self.fields.iteritems():
            if isinstance(v, remoteobjects.fields.Field):
                if getattr(self, k) != getattr(other, k):
                    return False
        return True

    def __ne__(self, other):
        """Returns whether two `DataObject` instances are different.

        `DataObject` instances are different if they are not equivalent as
        determined through `__eq__`.

        """
        return not self == other

    def to_dict(self):
        """Encodes the DataObject to a dictionary."""
        try:
            # TODO: this shallow copy only prevents sticky modification of the
            # dict's contents, not the contents' contents.
            data = dict(self._originaldata)
        except AttributeError:
            data = {}

        for field_name, field in self.fields.iteritems():
            if hasattr(field, 'encode_into'):
                field.encode_into(self, data, field_name=field_name)
        return data

    @classmethod
    def from_dict(cls, data):
        """Decodes a dictionary into a new `DataObject` instance."""
        self = cls()
        self.update_from_dict(data)
        return self

    def update_from_dict(self, data):
        """Adds the content of a dictionary to this DataObject.

        Parameter `data` is the dictionary from which to update the object.

        Use this only when receiving newly updated or partial content for a
        DataObject; that is, when the data is from the outside data source and
        needs decoded through the object's fields. Data from "inside" your
        application should be added to an object manually by setting the
        object's attributes. Data that constitutes a new object should be
        turned into another object with `from_dict()`.

        """
        # Remember this extra data, so we can play it back later.
        if not hasattr(self, '_originaldata'):
            self._originaldata = {}
        self._originaldata.update(data)

        for field_name, field in self.fields.iteritems():
            if hasattr(field, 'decode_into'):
                field.decode_into(data, self, field_name=field_name)
