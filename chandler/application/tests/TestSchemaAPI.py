import unittest
this_module = "application.tests.TestSchemaAPI"     # change this if it moves

from application import schema, tests
from repository.schema import Types
from repository.persistence.RepositoryView import NullRepositoryView

class Dummy(schema.Item):
    """Just a test fixture"""
    attr = schema.One(schema.Text)
    other = schema.Many("Other", inverse="thing")

class Other(schema.Item):
    thing = schema.One(Dummy, inverse="other")

TEST_PATH = "//this/is/a/test"

class Mixed(Dummy, Types.Type):
    __default_path__ = TEST_PATH

class AnEnum(schema.Enumeration):
    values = "yes", "no"

class CoreAnnotation(schema.Annotation):
    schema.kindInfo(annotates=schema.Kind)
    extraInfo = schema.One(schema.Text)
    otherItem = schema.One(schema.Item, inverse=schema.Sequence())

class SchemaTestCase(unittest.TestCase):
    """Reset the schema API between unit tests"""

    def setUp(self):
        self.rv = NullRepositoryView(verify=True)

    def tearDown(self):
        self.failUnless(self.rv.check(), "check() failed")

class SchemaTests(SchemaTestCase):

    def testDeriveFromCore(self):
        self.assertEqual(
            list(schema.itemFor(Mixed, self.rv).superKinds),
            [schema.itemFor(Dummy, self.rv), schema.itemFor(Types.Type, self.rv)]
        )

    def testResetCache(self):
        # Parcel/kind/attr caches should be cleared between resets
        schema.reset()
        rv = schema._get_nrv()
        parcel1 = schema.parcel_for_module(this_module, rv)
        kind1 = schema.itemFor(Dummy, rv)
        attr1 = schema.itemFor(Dummy.attr, rv)

        old = schema.reset()
        rv = schema._get_nrv()
        parcel2 = schema.parcel_for_module(this_module, rv)
        kind2 = schema.itemFor(Dummy, rv)
        attr2 = schema.itemFor(Dummy.attr, rv)

        self.failIf(parcel2 is parcel1)
        self.failIf(kind2 is kind1)
        self.failIf(attr2 is attr1)

        # But switching back to an old state should restore the cache
        schema.reset(old)
        rv = schema._get_nrv()
        parcel3 = schema.parcel_for_module(this_module, rv)
        kind3 = schema.itemFor(Dummy, rv)
        attr3 = schema.itemFor(Dummy.attr, rv)
        self.failUnless(parcel3 is parcel1)
        self.failUnless(attr3 is attr1)
        self.failUnless(attr3 is attr1)

    def testAttrKindType(self):
        self.assertEqual(schema.itemFor(Dummy.attr, self.rv).getAspect('type'),
            self.rv.findPath('//Schema/Core/Text'))
        self.assertEqual(schema.itemFor(Other.thing, self.rv).getAspect('type'),
                         schema.itemFor(Dummy, self.rv))
        self.assertRaises(TypeError, schema.Descriptor, str)

    def testImportAll(self):
        schema.initRepository(self.rv)

        # Verify that //userdata and the test default path don't exist
        self.assertRaises(KeyError, lambda: self.rv['userdata'])
        self.assertEqual( self.rv.findPath(TEST_PATH), None)

        schema.synchronize(self.rv, this_module)
        path = "//parcels/%s/" % this_module.replace('.','/')

        # Everything should exist now, including the default parent objects        
        self.assertNotEqual( self.rv.findPath(TEST_PATH), None)
        self.assertNotEqual( self.rv.findPath("//userdata"), None)
        self.assertNotEqual( self.rv.findPath(path+'Dummy'), None)
        self.assertNotEqual( self.rv.findPath(path+'AnEnum'), None)

    def testAnnotateKind(self):
        kind_kind = schema.itemFor(schema.Kind, self.rv)
        CoreAnnotation(kind_kind).extraInfo = u"Foo"
        self.assertEqual(CoreAnnotation(kind_kind).extraInfo, u"Foo")
        parcel = schema.parcel_for_module(__name__, self.rv)
        CoreAnnotation(kind_kind).otherItem = parcel
        self.assertEqual(
            list(getattr(parcel, __name__+".CoreAnnotation.otherItem.inverse")),
            [kind_kind]
        )


def test_schema_api():
    import doctest
    return doctest.DocFileSuite(
        'parcel-schema-guide.txt',
        'schema_api.txt',
        optionflags=doctest.ELLIPSIS, package='application',
        globs=tests.__dict__
    )


def additional_tests():
    return unittest.TestSuite(
        [ test_schema_api(), ]
    )


if __name__=='__main__':
    # This module can't be safely run as __main__, so it has to be re-imported
    # and have *that* copy run.
    from run_tests import ScanningLoader
    unittest.main(
        module=None, testLoader = ScanningLoader(),
        argv=["unittest", this_module]
    )
else:
    assert __name__ == this_module, (
        "This module must be installed in its designated location"
    )
