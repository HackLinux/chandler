
/*
 * The C attribute types
 *
 * Copyright (c) 2003-2005 Open Source Applications Foundation
 * License at http://osafoundation.org/Chandler_0.1_license_terms.htm
 */

#include <Python.h>
#include "structmember.h"

#include "c.h"

static void t_attribute_dealloc(t_attribute *self);
static int t_attribute_traverse(t_attribute *self, visitproc visit, void *arg);
static int t_attribute_clear(t_attribute *self);
static PyObject *t_attribute_new(PyTypeObject *type,
                                 PyObject *args, PyObject *kwds);
static int t_attribute_init(t_attribute *self, PyObject *args, PyObject *kwds);

static PyObject *t_attribute_getAspect(t_attribute *self, PyObject *args);

static PyObject *t_attribute__getCardinality(t_attribute *self, void *data);
static int t_attribute__setCardinality(t_attribute *self, PyObject *value,
                                       void *data);
static PyObject *t_attribute__getPersisted(t_attribute *self, void *data);
static int t_attribute__setPersisted(t_attribute *self, PyObject *value,
                                     void *data);
static PyObject *t_attribute__getRequired(t_attribute *self, void *data);
static int t_attribute__setRequired(t_attribute *self, PyObject *value,
                                    void *data);
static PyObject *t_attribute__getIndexed(t_attribute *self, void *data);
static int t_attribute__setIndexed(t_attribute *self, PyObject *value,
                                   void *data);
static PyObject *t_attribute__getNoInherit(t_attribute *self, void *data);
static int t_attribute__setNoInherit(t_attribute *self, PyObject *value,
                                     void *data);
static PyObject *t_attribute__getRedirectTo(t_attribute *self, void *data);
static int t_attribute__setRedirectTo(t_attribute *self, PyObject *value,
                                      void *data);
static PyObject *t_attribute__getOtherName(t_attribute *self, void *data);
static int t_attribute__setOtherName(t_attribute *self, PyObject *value,
                                     void *data);
static PyObject *t_attribute__getTypeID(t_attribute *self, void *data);
static int t_attribute__setTypeID(t_attribute *self, PyObject *value,
                                  void *data);
static PyObject *t_attribute__getProcess(t_attribute *self, void *data);

static PyObject *_getRef_NAME;
static PyObject *getFlags_NAME;
static PyObject *persisted_NAME;
static PyObject *cardinality_NAME;
static PyObject *single_NAME, *list_NAME, *dict_NAME, *set_NAME;
static PyObject *required_NAME;
static PyObject *indexed_NAME;
static PyObject *otherName_NAME;
static PyObject *redirectTo_NAME;
static PyObject *inheritFrom_NAME;
static PyObject *defaultValue_NAME;
static PyObject *type_NAME;
static PyObject *_item_NAME;

static PyMemberDef t_attribute_members[] = {
    { "attrID", T_OBJECT, offsetof(t_attribute, attrID), READONLY,
      "attribute uuid" },
    { "flags", T_INT, offsetof(t_attribute, flags), 0,
      "attribute flags" },
    { NULL, 0, 0, 0, NULL }
};

static PyMethodDef t_attribute_methods[] = {
    { "getAspect", (PyCFunction) t_attribute_getAspect, METH_VARARGS, "" },
    { NULL, NULL, 0, NULL }
};

static PyGetSetDef t_attribute_properties[] = {
    { "cardinality",
      (getter) t_attribute__getCardinality,
      (setter) t_attribute__setCardinality,
      "cardinality property", NULL },
    { "persisted",
      (getter) t_attribute__getPersisted,
      (setter) t_attribute__setPersisted,
      "persisted property", NULL },
    { "required",
      (getter) t_attribute__getRequired,
      (setter) t_attribute__setRequired,
      "required property", NULL },
    { "indexed",
      (getter) t_attribute__getIndexed,
      (setter) t_attribute__setIndexed,
      "indexed property", NULL },
    { "noInherit",
      (getter) t_attribute__getNoInherit,
      (setter) t_attribute__setNoInherit,
      "noInherit property", NULL },
    { "redirectTo",
      (getter) t_attribute__getRedirectTo,
      (setter) t_attribute__setRedirectTo,
      "redirectTo property", NULL },
    { "otherName",
      (getter) t_attribute__getOtherName,
      (setter) t_attribute__setOtherName,
      "otherName property", NULL },
    { "typeID",
      (getter) t_attribute__getTypeID,
      (setter) t_attribute__setTypeID,
      "typeID property", NULL },
    { "process",
      (getter) t_attribute__getProcess,
      NULL,
      "process property", NULL },
    { NULL, NULL, NULL, NULL, NULL }
};

static PyTypeObject AttributeType = {
    PyObject_HEAD_INIT(NULL)
    0,                                          /* ob_size */
    "chandlerdb.schema.c.CAttribute",           /* tp_name */
    sizeof(t_attribute),                        /* tp_basicsize */
    0,                                          /* tp_itemsize */
    (destructor)t_attribute_dealloc,            /* tp_dealloc */
    0,                                          /* tp_print */
    0,                                          /* tp_getattr */
    0,                                          /* tp_setattr */
    0,                                          /* tp_compare */
    0,                                          /* tp_repr */
    0,                                          /* tp_as_number */
    0,                                          /* tp_as_sequence */
    0,                                          /* tp_as_mapping */
    0,                                          /* tp_hash  */
    0,                                          /* tp_call */
    0,                                          /* tp_str */
    0,                                          /* tp_getattro */
    0,                                          /* tp_setattro */
    0,                                          /* tp_as_buffer */
    (Py_TPFLAGS_DEFAULT |
     Py_TPFLAGS_BASETYPE |
     Py_TPFLAGS_HAVE_GC),                       /* tp_flags */
    "attribute",                                /* tp_doc */
    (traverseproc)t_attribute_traverse,         /* tp_traverse */
    (inquiry)t_attribute_clear,                 /* tp_clear */
    0,                                          /* tp_richcompare */
    0,                                          /* tp_weaklistoffset */
    0,                                          /* tp_iter */
    0,                                          /* tp_iternext */
    t_attribute_methods,                        /* tp_methods */
    t_attribute_members,                        /* tp_members */
    t_attribute_properties,                     /* tp_getset */
    0,                                          /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    (initproc)t_attribute_init,                 /* tp_init */
    0,                                          /* tp_alloc */
    (newfunc)t_attribute_new,                   /* tp_new */
};


static void t_attribute_dealloc(t_attribute *self)
{
    t_attribute_clear(self);
    self->ob_type->tp_free((PyObject *) self);
}

static int t_attribute_traverse(t_attribute *self, visitproc visit, void *arg)
{
    Py_VISIT(self->attrID);
    Py_VISIT(self->otherName);
    Py_VISIT(self->redirectTo);
    Py_VISIT(self->typeID);

    return 0;
}

static int t_attribute_clear(t_attribute *self)
{
    Py_CLEAR(self->attrID);
    Py_CLEAR(self->otherName);
    Py_CLEAR(self->redirectTo);
    Py_CLEAR(self->typeID);

    return 0;
}


static PyObject *t_attribute_new(PyTypeObject *type,
                                 PyObject *args, PyObject *kwds)
{
    t_attribute *self = (t_attribute *) type->tp_alloc(type, 0);

    if (self)
    {
        self->attrID = NULL;
        self->otherName = NULL;
        self->redirectTo = NULL;
        self->typeID = NULL;
    }

    return (PyObject *) self;
}

static int t_attribute_init(t_attribute *self, PyObject *args, PyObject *kwds)
{
    PyObject *attribute;

    if (!PyArg_ParseTuple(args, "O", &attribute))
        return -1;
    else
    {
        PyObject *values = ((t_item *) attribute)->values;
        PyObject *cardinality = PyDict_GetItem(values, cardinality_NAME);
        PyObject *inheritFrom = PyDict_GetItem(values, inheritFrom_NAME);
        PyObject *defaultValue = PyDict_GetItem(values, defaultValue_NAME);
        PyObject *redirectTo = PyDict_GetItem(values, redirectTo_NAME);
        int flags = NOINHERIT;

        if (!cardinality)
            flags |= SINGLE;
        else if (!PyObject_Compare(cardinality, single_NAME))
            flags |= SINGLE;
        else if (!PyObject_Compare(cardinality, list_NAME))
            flags |= LIST;
        else if (!PyObject_Compare(cardinality, dict_NAME))
            flags |= DICT;
        else if (!PyObject_Compare(cardinality, set_NAME))
            flags |= SET;

        if (PyDict_GetItem(values, persisted_NAME) == Py_False)
            flags |= TRANSIENT;

        if (PyDict_GetItem(values, required_NAME) == Py_True)
            flags |= REQUIRED;

        if (PyDict_GetItem(values, indexed_NAME) == Py_True)
            flags |= INDEXED;

        if ((inheritFrom != NULL && inheritFrom != Py_None) ||
            (defaultValue != NULL))
        {
            flags &= ~NOINHERIT;
        }

        if (redirectTo != NULL && redirectTo != Py_None)
        {
            flags |= REDIRECT | PROCESS;
            flags &= ~NOINHERIT;

            Py_INCREF(redirectTo);
            self->redirectTo = redirectTo;
        }
        else
        {
            PyObject *otherName = PyDict_GetItem(values, otherName_NAME);

            if (otherName != NULL && otherName != Py_None)
            {
                if (flags & SINGLE)
                    flags |= PROCESS;

                flags |= REF;

                Py_INCREF(otherName);
                self->otherName = otherName;
            }
        }

        if (!(flags & (REF | REDIRECT)))
        {
            PyObject *references = ((t_item *) attribute)->references;

            if (PyDict_Contains(references, type_NAME))
            {
                PyObject *type = PyObject_CallMethodObjArgs(references, _getRef_NAME, type_NAME, Py_None, Py_None, NULL);

                if (type == NULL)
                    return -1;

                if (type == Py_None)
                    self->typeID = type;
                else if (!PyObject_TypeCheck(type, CItem))
                {
                    PyErr_SetObject(PyExc_TypeError, type);
                    Py_DECREF(type);
                    return -1;
                }
                else
                {
                    PyObject *typeFlags =
                        PyObject_CallMethodObjArgs(type, getFlags_NAME, NULL);
                    PyObject *uuid = ((t_item *) type)->uuid;

                    Py_INCREF(uuid);
                    self->typeID = uuid;

                    Py_DECREF(type);

                    if (typeFlags == NULL)
                        return -1;

                    if (!PyInt_Check(typeFlags))
                    {
                        PyErr_SetObject(PyExc_TypeError, typeFlags);
                        Py_DECREF(typeFlags);

                        return -1;
                    }

                    flags |= PyInt_AsLong(typeFlags);
                    Py_DECREF(typeFlags);
                }
            }
            else
                flags |= PROCESS;

            flags |= VALUE;
        }

        self->flags = flags;
        self->attrID = ((t_item *) attribute)->uuid; Py_INCREF(self->attrID);

        return 0;
    }
}

static PyObject *t_attribute_getAspect(t_attribute *self, PyObject *args)
{
    PyObject *aspect, *defaultValue;

    if (!PyArg_ParseTuple(args, "OO", &aspect, &defaultValue))
        return NULL;
    else
    {
        int flags = self->flags;
                    
        if (!(flags & REDIRECT))
        {
            if (!PyObject_Compare(aspect, persisted_NAME))
            {
                if (flags & TRANSIENT)
                    Py_RETURN_FALSE;

                Py_RETURN_TRUE;
            }

            else if (!PyObject_Compare(aspect, redirectTo_NAME))
                Py_RETURN_NONE;

            else if (!PyObject_Compare(aspect, cardinality_NAME))
                return t_attribute__getCardinality(self, NULL);

            else if (!PyObject_Compare(aspect, otherName_NAME))
            {
                if (flags & REF)
                {
                    Py_INCREF(self->otherName);
                    return self->otherName;
                }
            }

            else if (!PyObject_Compare(aspect, required_NAME))
            {
                if (flags & REQUIRED)
                    Py_RETURN_TRUE;

                Py_RETURN_FALSE;
            }

            else if (!PyObject_Compare(aspect, indexed_NAME))
            {
                if (flags & INDEXED)
                    Py_RETURN_TRUE;

                Py_RETURN_FALSE;
            }
        }
        else if (!PyObject_Compare(aspect, redirectTo_NAME))
        {
            Py_INCREF(self->redirectTo);
            return self->redirectTo;
        }

        Py_INCREF(defaultValue);
        return defaultValue;
    }
}


/* cardinality */

static PyObject *t_attribute__getCardinality(t_attribute *self, void *data)
{
    if (!(self->flags & REDIRECT))
    {
        PyObject *value = NULL;

        switch (self->flags & CARDINALITY) {
          case SINGLE:
            value = single_NAME;
            break;
          case LIST:
            value = list_NAME;
            break;
          case DICT:
            value = dict_NAME;
            break;
          case SET:
            value = set_NAME;
            break;
          default:
            value = single_NAME;
            break;
        }

        Py_INCREF(value);
        return value;
    }

    PyErr_SetString(PyExc_AttributeError, "cardinality");
    return NULL;
}

static int t_attribute__setCardinality(t_attribute *self, PyObject *value,
                                       void *data)
{
    if (!PyDict_Check(value))
    {
        PyErr_SetObject(PyExc_TypeError, value);
        return -1;
    }
    else
    {
        PyObject *cardinality = PyDict_GetItem(value, cardinality_NAME);

        self->flags &= ~CARDINALITY;
    
        if (!cardinality || !PyObject_Compare(cardinality, single_NAME))
            self->flags |= SINGLE;
        else if (!PyObject_Compare(cardinality, list_NAME))
            self->flags |= LIST;
        else if(!PyObject_Compare(cardinality, dict_NAME))
            self->flags |= DICT;
        else if (!PyObject_Compare(cardinality, set_NAME))
            self->flags |= SET;
        else
        {
            PyErr_SetObject(PyExc_ValueError, value);
            return -1;
        }

        if (self->flags & REF)
            return t_attribute__setOtherName(self, value, data);

        return 0;
    }
}

/* persisted property */

static PyObject *t_attribute__getPersisted(t_attribute *self, void *data)
{
    if (!(self->flags & REDIRECT))
    {
        if (self->flags & TRANSIENT)
            Py_RETURN_FALSE;

        Py_RETURN_TRUE;    
    }

    PyErr_SetString(PyExc_AttributeError, "persisted");
    return NULL;
}

static int t_attribute__setPersisted(t_attribute *self, PyObject *value,
                                     void *data)
{
    if (value == Py_True)
        self->flags &= ~TRANSIENT;
    else if (value == Py_False)
        self->flags |= TRANSIENT;
    else
    {
        PyErr_SetObject(PyExc_ValueError, value);
        return -1;
    }

    return 0;
}

/* required property */

static PyObject *t_attribute__getRequired(t_attribute *self, void *data)
{
    if (!(self->flags & REDIRECT))
    {
        if (self->flags & REQUIRED)
            Py_RETURN_TRUE;

        Py_RETURN_FALSE;    
    }

    PyErr_SetString(PyExc_AttributeError, "required");
    return NULL;
}

static int t_attribute__setRequired(t_attribute *self, PyObject *value,
                                    void *data)
{
    if (value == Py_True)
        self->flags |= REQUIRED;
    else if (value == Py_False)
        self->flags &= ~REQUIRED;
    else
    {
        PyErr_SetObject(PyExc_ValueError, value);
        return -1;
    }

    return 0;
}

/* indexed property */

static PyObject *t_attribute__getIndexed(t_attribute *self, void *data)
{
    if (!(self->flags & REDIRECT))
    {
        if (self->flags & INDEXED)
            Py_RETURN_TRUE;

        Py_RETURN_FALSE;    
    }

    PyErr_SetString(PyExc_AttributeError, "indexed");
    return NULL;
}

static int t_attribute__setIndexed(t_attribute *self, PyObject *value,
                                    void *data)
{
    if (value == Py_True)
        self->flags |= INDEXED;
    else if (value == Py_False)
        self->flags &= ~INDEXED;
    else
    {
        PyErr_SetObject(PyExc_ValueError, value);
        return -1;
    }

    return 0;
}

/* noInherit property */

static PyObject *t_attribute__getNoInherit(t_attribute *self, void *data)
{
    if (self->flags & NOINHERIT)
        Py_RETURN_TRUE;

    Py_RETURN_FALSE;
}

static int t_attribute__setNoInherit(t_attribute *self, PyObject *value,
                                     void *data)
{
    if (!PyTuple_CheckExact(value))
    {
        PyErr_SetObject(PyExc_TypeError, value);
        return -1;
    }
    else if (!PyTuple_Size(value) == 4)
    {
        PyErr_SetObject(PyExc_ValueError, value);
        return -1;
    }
    else
    {
        PyObject *values = PyTuple_GET_ITEM(value, 0);
        PyObject *n1 = PyTuple_GET_ITEM(value, 1);
        PyObject *n2 = PyTuple_GET_ITEM(value, 2);
        PyObject *n3 = PyTuple_GET_ITEM(value, 3);
        PyObject *v1 = PyDict_GetItem(values, n1);
        PyObject *v2 = PyDict_GetItem(values, n2);
        PyObject *v3 = PyDict_GetItem(values, n3);

        if (v1 == NULL ||
            (v1 == Py_None && PyObject_Compare(n1, defaultValue_NAME)))
        {
            if ((v2 == NULL ||
                 (v2 == Py_None && PyObject_Compare(n2, defaultValue_NAME))) &&
                (v3 == NULL ||
                 (v3 == Py_None && PyObject_Compare(n3, defaultValue_NAME))))
                self->flags |= NOINHERIT;
        }
        else
            self->flags &= ~NOINHERIT;

        return 0;
    }
}

/* redirectTo property */

static PyObject *t_attribute__getRedirectTo(t_attribute *self, void *data)
{
    PyObject *value;

    if (self->flags & REDIRECT)
        value = self->redirectTo;
    else
        value = Py_None;

    Py_INCREF(value);
    return value;
}

static int t_attribute__setRedirectTo(t_attribute *self, PyObject *value,
                                      void *data)
{
    if (t_attribute__setNoInherit(self, value, data))
        return -1;
    else
    {
        PyObject *values = PyTuple_GET_ITEM(value, 0);
        PyObject *redirectTo = PyDict_GetItem(values, redirectTo_NAME);

        if (redirectTo)
            Py_INCREF(redirectTo);
        Py_XDECREF(self->redirectTo);
        self->redirectTo = redirectTo;

        self->flags &= ~ATTRDICT;
        if (redirectTo == NULL || redirectTo == Py_None)
        {
            self->flags &= ~(REDIRECT | PROCESS);
            return t_attribute__setOtherName(self, values, data);
        }
        else
        {
            self->flags |= REDIRECT | PROCESS;
            return 0;
        }
    }
}

/* otherName property */

static PyObject *t_attribute__getOtherName(t_attribute *self, void *data)
{
    if (!(self->flags & REDIRECT))
    {
        PyObject *value;

        if (self->flags & REF)
            value = self->otherName;
        else
            value = Py_None;

        Py_INCREF(value);
        return value;
    }

    PyErr_SetString(PyExc_AttributeError, "otherName");
    return NULL;
}

static int t_attribute__setOtherName(t_attribute *self, PyObject *value,
                                     void *data)
{
    if (!PyDict_Check(value))
    {
        PyErr_SetObject(PyExc_TypeError, value);
        return -1;
    }
    else
    {
        PyObject *otherName = PyDict_GetItem(value, otherName_NAME);

        if (otherName)
            Py_INCREF(otherName);
        Py_XDECREF(self->otherName);
        self->otherName = otherName;

        self->flags &= ~ATTRDICT;
        if (otherName == NULL || otherName == Py_None)
        {
            t_item *item = (t_item *) PyObject_GetAttr(value, _item_NAME);
            PyObject *references = item->references;

            Py_DECREF(item);
            return t_attribute__setTypeID(self, references, data);
        }
        else
        {
            self->flags |= REF;

            if (self->flags & SINGLE)
                self->flags |= PROCESS;
            else if (self->flags & LIST)
                self->flags &= ~PROCESS;

            return 0;
        }
    }
}

/* typeID property */

static PyObject *t_attribute__getTypeID(t_attribute *self, void *data)
{
    if (!(self->flags & (REDIRECT | REF)))
    {
        PyObject *value;

        if (self->flags & VALUE)
        {
            if (self->typeID == NULL)
                value = Py_None;
            else
                value = self->typeID;
        }
        else
            value = Py_None;

        Py_INCREF(value);
        return value;
    }

    PyErr_SetString(PyExc_AttributeError, "typeID");
    return NULL;
}

static int t_attribute__setTypeID(t_attribute *self, PyObject *value,
                                  void *data)
{
    if (!(self->flags & (REDIRECT | REF)))
    {
        if (!PyDict_Check(value))
        {
            PyErr_SetObject(PyExc_TypeError, value);
            return -1;
        }
        else if (PyDict_Contains(value, type_NAME))
        {
            PyObject *type =
                PyObject_CallMethodObjArgs(value, _getRef_NAME, type_NAME,
                                           Py_None, Py_None, NULL);

            if (type == Py_None)
            {
                self->flags |= PROCESS;
                Py_XDECREF(self->typeID);
                self->typeID = NULL;
            }
            else
            {
                PyObject *typeFlags =
                    PyObject_CallMethodObjArgs(type, getFlags_NAME, NULL);

                if (!typeFlags)
                    return -1;

                if (!PyInt_Check(typeFlags))
                {
                    PyErr_SetObject(PyExc_TypeError, typeFlags);
                    Py_DECREF(typeFlags);

                    return -1;
                }

                self->flags &= ~PROCESS;
                self->flags |= PyInt_AsLong(typeFlags);
                Py_DECREF(typeFlags);

                Py_INCREF(((t_item *) type)->uuid);
                Py_XDECREF(self->typeID);
                self->typeID = ((t_item *) type)->uuid;
            }
        }
        else
        {
            self->flags |= PROCESS;
            Py_XDECREF(self->typeID);
            self->typeID = NULL;
        }
        
        self->flags |= VALUE;
    }

    return 0;
}

/* process property */

static PyObject *t_attribute__getProcess(t_attribute *self, void *data)
{
    return PyInt_FromLong(self->flags & PROCESS);
}


void _init_attribute(PyObject *m)
{
    if (PyType_Ready(&AttributeType) >= 0)
    {
        if (m)
        {
            PyObject *dict;

            Py_INCREF(&AttributeType);
            PyModule_AddObject(m, "CAttribute", (PyObject *) &AttributeType);

            CAttribute = &AttributeType;

            dict = AttributeType.tp_dict;
            PyDict_SetItemString_Int(dict, "VALUE", VALUE);
            PyDict_SetItemString_Int(dict, "REF", REF);
            PyDict_SetItemString_Int(dict, "REDIRECT", REDIRECT);
            PyDict_SetItemString_Int(dict, "REQUIRED", REQUIRED);
            PyDict_SetItemString_Int(dict, "INDEXED", INDEXED);
            PyDict_SetItemString_Int(dict, "PROCESS_GET", PROCESS_GET);
            PyDict_SetItemString_Int(dict, "PROCESS_SET", PROCESS_SET);
            PyDict_SetItemString_Int(dict, "SINGLE", SINGLE);
            PyDict_SetItemString_Int(dict, "LIST", LIST);
            PyDict_SetItemString_Int(dict, "DICT", DICT);
            PyDict_SetItemString_Int(dict, "SET", SET);
            PyDict_SetItemString_Int(dict, "ALIAS", ALIAS);
            PyDict_SetItemString_Int(dict, "KIND", KIND);
            PyDict_SetItemString_Int(dict, "NOINHERIT", NOINHERIT);
            PyDict_SetItemString_Int(dict, "TRANSIENT", TRANSIENT);
            PyDict_SetItemString_Int(dict, "PROCESS", PROCESS);
            PyDict_SetItemString_Int(dict, "CARDINALITY", CARDINALITY);
            PyDict_SetItemString_Int(dict, "ATTRDICT", ATTRDICT);

            _getRef_NAME = PyString_FromString("_getRef");
            getFlags_NAME = PyString_FromString("getFlags");
            persisted_NAME = PyString_FromString("persisted");
            cardinality_NAME = PyString_FromString("cardinality");
            single_NAME = PyString_FromString("single");
            list_NAME = PyString_FromString("list");
            dict_NAME = PyString_FromString("dict");
            set_NAME = PyString_FromString("set");
            required_NAME = PyString_FromString("required");
            indexed_NAME = PyString_FromString("indexed");
            otherName_NAME = PyString_FromString("otherName");
            redirectTo_NAME = PyString_FromString("redirectTo");
            inheritFrom_NAME = PyString_FromString("inheritFrom");
            defaultValue_NAME = PyString_FromString("defaultValue");
            type_NAME = PyString_FromString("type");
            _item_NAME = PyString_FromString("_item");
        }
    }
}
