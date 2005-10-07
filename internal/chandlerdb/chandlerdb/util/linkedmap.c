
/*
 * The C LinkedMap type
 *
 * Copyright (c) 2003-2005 Open Source Applications Foundation
 * License at http://osafoundation.org/Chandler_0.1_license_terms.htm
 */

#include <Python.h>
#include "structmember.h"

#include "c.h"

static void t_link_dealloc(t_link *self);
static int t_link_traverse(t_link *self, visitproc visit, void *arg);
static int t_link_clear(t_link *self);
static PyObject *t_link_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static int t_link_init(t_link *self, PyObject *args, PyObject *kwds);
static PyObject *t_link_repr(t_link *self);

static PyObject *t_link__copy_(t_link *self, PyObject *arg);

static PyObject *t_link__getPreviousKey(t_link *self, void *data);
static int _t_link_setPreviousKey(t_link *self,
                                  PyObject *previousKey, PyObject *key);
static int _t_link_setNextKey(t_link *self,
                              PyObject *nextKey, PyObject *key);
static int t_link__setPreviousKey(t_link *self, PyObject *value, void *data);
static PyObject *t_link__getNextKey(t_link *self, void *data);
static int t_link__setNextKey(t_link *self, PyObject *value, void *data);
static PyObject *t_link_getValue(t_link *self, void *data);
static int t_link_setValue(t_link *self, PyObject *arg, void *data);
static PyObject *t_link_getAlias(t_link *self, void *data);
static int t_link_setAlias(t_link *self, PyObject *arg, void *data);


static PyObject *t_lm_has_key(t_lm *self, PyObject *key);
static PyObject *t_lm_get(t_lm *self, PyObject *args);
static PyObject *_t_lm__get(t_lm *self, PyObject *key, int load);
static PyObject *t_lm__get(t_lm *self, PyObject *args);
static PyObject *t_lm_dict_clear(t_lm *self, PyObject *args);

static PyObject *t_lm__getDict(t_lm *self, void *data);
static PyObject *t_lm__getAliases(t_lm *self, void *data);

static PyObject *t_lm__getFirstKey(t_lm *self, void *data);
static int t_lm___setFirstKey(t_lm *self, PyObject *arg, void *data);
static PyObject *t_lm__getLastKey(t_lm *self, void *data);
static int t_lm___setLastKey(t_lm *self, PyObject *arg, void *data);

static PyObject *_load_NAME;
static PyObject *linkChanged_NAME;
static PyObject *view_NAME;


static PyMemberDef t_link_members[] = {
    { "_value", T_OBJECT, offsetof(t_link, value), 0, "" },
    { NULL, 0, 0, 0, NULL }
};

static PyMethodDef t_link_methods[] = {
    { "_copy_", (PyCFunction) t_link__copy_, METH_O, "" },
    { NULL, NULL, 0, NULL }
};

static PyGetSetDef t_link_properties[] = {
    { "_previousKey",
      (getter) t_link__getPreviousKey,
      (setter) t_link__setPreviousKey,
      "", NULL },
    { "_nextKey",
      (getter) t_link__getNextKey,
      (setter) t_link__setNextKey,
      "", NULL },
    { "value",
      (getter) t_link_getValue,
      (setter) t_link_setValue,
      "", NULL },
    { "alias",
      (getter) t_link_getAlias,
      (setter) t_link_setAlias,
      "", NULL },
    { NULL, NULL, NULL, NULL, NULL }
};


static PyTypeObject LinkType = {
    PyObject_HEAD_INIT(NULL)
    0,                                /* ob_size */
    "chandlerdb.util.c.Link",         /* tp_name */
    sizeof(t_link),                   /* tp_basicsize */
    0,                                /* tp_itemsize */
    (destructor)t_link_dealloc,       /* tp_dealloc */
    0,                                /* tp_print */
    0,                                /* tp_getattr */
    0,                                /* tp_setattr */
    0,                                /* tp_compare */
    (reprfunc)t_link_repr,            /* tp_repr */
    0,                                /* tp_as_number */
    0,                                /* tp_as_sequence */
    0,                                /* tp_as_mapping */
    0,                                /* tp_hash  */
    0,                                /* tp_call */
    0,                                /* tp_str */
    0,                                /* tp_getattro */
    0,                                /* tp_setattro */
    0,                                /* tp_as_buffer */
    (Py_TPFLAGS_DEFAULT |
     Py_TPFLAGS_BASETYPE |
     Py_TPFLAGS_HAVE_GC),             /* tp_flags */
    "t_link objects",                 /* tp_doc */
    (traverseproc)t_link_traverse,    /* tp_traverse */
    (inquiry)t_link_clear,            /* tp_clear */
    0,                                /* tp_richcompare */
    0,                                /* tp_weaklistoffset */
    0,                                /* tp_iter */
    0,                                /* tp_iternext */
    t_link_methods,                   /* tp_methods */
    t_link_members,                   /* tp_members */
    t_link_properties,                /* tp_getset */
    0,                                /* tp_base */
    0,                                /* tp_dict */
    0,                                /* tp_descr_get */
    0,                                /* tp_descr_set */
    0,                                /* tp_dictoffset */
    (initproc)t_link_init,            /* tp_init */
    0,                                /* tp_alloc */
    (newfunc)t_link_new,              /* tp_new */
};


static void t_link_dealloc(t_link *self)
{
    t_link_clear(self);
    self->ob_type->tp_free((PyObject *) self);
}

static int t_link_traverse(t_link *self, visitproc visit, void *arg)
{
    Py_VISIT(self->owner);
    Py_VISIT(self->previousKey);
    Py_VISIT(self->nextKey);
    Py_VISIT(self->value);
    Py_VISIT(self->alias);

    return 0;
}

static int t_link_clear(t_link *self)
{
    Py_CLEAR(self->owner);
    Py_CLEAR(self->previousKey);
    Py_CLEAR(self->nextKey);
    Py_CLEAR(self->value);
    Py_CLEAR(self->alias);

    return 0;
}

static PyObject *t_link_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    t_link *self = (t_link *) type->tp_alloc(type, 0);

    if (self)
    {
        self->owner = NULL;
        self->previousKey = NULL;
        self->nextKey = NULL;
        self->value = NULL;
        self->alias = NULL;
    }

    return (PyObject *) self;
}

static int t_link_init(t_link *self, PyObject *args, PyObject *kwds)
{
    PyObject *owner, *value;
    PyObject *previousKey = Py_None, *nextKey = Py_None, *alias = Py_None;

    if (!PyArg_ParseTuple(args, "OO|OOO", &owner, &value,
                          &previousKey, &nextKey, &alias))
        return -1;
    else
    {
        Py_INCREF(owner); Py_XDECREF(self->owner);
        self->owner = owner;

        Py_INCREF(value); Py_XDECREF(self->value);
        self->value = value;

        Py_INCREF(previousKey); Py_XDECREF(self->previousKey);
        self->previousKey = previousKey;

        Py_INCREF(nextKey); Py_XDECREF(self->nextKey);
        self->nextKey = nextKey;

        Py_INCREF(alias); Py_XDECREF(self->alias);
        self->alias = alias;
    }

    return 0;
}

static PyObject *t_link_repr(t_link *self)
{
    PyObject *value = PyObject_Repr(self->value);
    PyObject *repr = PyString_FromFormat("<link: %s>",
                                         PyString_AsString(value));
    Py_DECREF(value);

    return repr;
}

static PyObject *t_link__copy_(t_link *self, PyObject *arg)
{
    if (!PyObject_TypeCheck(arg, &LinkType))
    {
        PyErr_SetObject(PyExc_TypeError, arg);
        return NULL;
    }
    else
    {
        PyObject *obj;

        obj = ((t_link *) arg)->previousKey;
        Py_INCREF(obj); Py_XDECREF(self->previousKey);
        self->previousKey = obj;

        obj = ((t_link *) arg)->nextKey;
        Py_INCREF(obj); Py_XDECREF(self->nextKey);
        self->nextKey = obj;

        obj = ((t_link *) arg)->alias;
        Py_INCREF(obj); Py_XDECREF(self->alias);
        self->alias = obj;

        Py_RETURN_NONE;
    }
}


/* _previousKey property */

static PyObject *t_link__getPreviousKey(t_link *self, void *data)
{
    PyObject *previousKey = self->previousKey;

    Py_INCREF(previousKey);
    return previousKey;
}

static int _t_link_setPreviousKey(t_link *self,
                                  PyObject *previousKey, PyObject *key)
{
    t_lm *owner = (t_lm *) self->owner;
    PyObject *result;

    if (previousKey == Py_None)
    {
        t_lm___setFirstKey(owner, key, NULL);

        result =
            PyObject_CallMethodObjArgs((PyObject *) owner, linkChanged_NAME,
                                       owner->head, Py_None, NULL);
        if (!result)
            return -1;
        Py_DECREF(result);
    }

    Py_INCREF(previousKey); Py_XDECREF(self->previousKey);
    self->previousKey = previousKey;

    result =
        PyObject_CallMethodObjArgs((PyObject *) owner, linkChanged_NAME,
                                   self, key, NULL);
    if (!result)
        return -1;
    Py_DECREF(result);
        
    return 0;
}

static int t_link__setPreviousKey(t_link *self, PyObject *value, void *data)
{
    PyObject *previousKey, *key;

    if (!PyArg_ParseTuple(value, "OO", &previousKey, &key))
        return -1;
    else
        return _t_link_setPreviousKey(self, previousKey, key);
}


/* _nextKey property */

static PyObject *t_link__getNextKey(t_link *self, void *data)
{
    PyObject *nextKey = self->nextKey;

    Py_INCREF(nextKey);
    return nextKey;
}

static int _t_link_setNextKey(t_link *self, PyObject *nextKey, PyObject *key)
{
    t_lm *owner = (t_lm *) self->owner;
    PyObject *result;

    if (nextKey == Py_None)
    {
        t_lm___setLastKey(owner, key, NULL);

        result =
            PyObject_CallMethodObjArgs((PyObject *) owner, linkChanged_NAME,
                                       owner->head, Py_None, NULL);
        if (!result)
            return -1;
        Py_DECREF(result);
    }

    Py_INCREF(nextKey); Py_XDECREF(self->nextKey);
    self->nextKey = nextKey;

    result =
        PyObject_CallMethodObjArgs((PyObject *) owner, linkChanged_NAME,
                                   self, key, NULL);
    if (!result)
        return -1;
    Py_DECREF(result);
        
    return 0;
}

static int t_link__setNextKey(t_link *self, PyObject *value, void *data)
{
    PyObject *nextKey, *key;

    if (!PyArg_ParseTuple(value, "OO", &nextKey, &key))
        return -1;
    else
        return _t_link_setNextKey(self, nextKey, key);
}


/* value property */

static PyObject *t_link_getValue(t_link *self, void *data)
{
    t_lm *owner = (t_lm *) self->owner;
    PyObject *value = self->value;

    if (owner->flags & LM_LOAD && PyObject_TypeCheck(value, UUID))
    {
        PyObject *view = PyObject_GetAttr((PyObject *) owner, view_NAME);

        if (!view)
            return NULL;

        value = PyObject_GetItem(view, value);
        Py_DECREF(view);

        if (!value)
            return NULL;
        
        Py_XDECREF(self->value);
        self->value = value;
    }
    else
        Py_INCREF(value);

    return value;
}

static int t_link_setValue(t_link *self, PyObject *value, void *data)
{
    Py_INCREF(value); Py_XDECREF(self->value);
    self->value = value;

    return 0;
}


/* alias property */

static PyObject *t_link_getAlias(t_link *self, void *data)
{
    PyObject *alias = self->alias;

    Py_INCREF(alias);
    return alias;
}

static int t_link_setAlias(t_link *self, PyObject *alias, void *data)
{
    Py_INCREF(alias); Py_XDECREF(self->alias);
    self->alias = alias;

    return 0;
}


static void t_lm_dealloc(t_lm *self);
static int t_lm_traverse(t_lm *self, visitproc visit, void *arg);
static int t_lm_clear(t_lm *self);
static PyObject *t_lm_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static int t_lm_init(t_lm *self, PyObject *args, PyObject *kwds);

static int t_lm_dict_length(t_lm *self);
static PyObject *t_lm_dict_get(t_lm *self, PyObject *key);
static int t_lm_dict_set(t_lm *self, PyObject *key, PyObject *value);

static PyObject *t_lm_previousKey(t_lm *self, PyObject *key);
static PyObject *t_lm_nextKey(t_lm *self, PyObject *key);


static PyMemberDef t_lm_members[] = {
    { "_flags", T_UINT, offsetof(t_lm, flags), 0, "" },
    { "_count", T_UINT, offsetof(t_lm, count), 0, "" },
    { "_head", T_OBJECT, offsetof(t_lm, head), READONLY, "" },
    { NULL, 0, 0, 0, NULL }
};

static PyMethodDef t_lm_methods[] = {
    { "get", (PyCFunction) t_lm_get, METH_VARARGS, "" },
    { "_get", (PyCFunction) t_lm__get, METH_VARARGS, "" },
    { "__contains__", (PyCFunction) t_lm_has_key, METH_O|METH_COEXIST, "" },
    { "has_key", (PyCFunction) t_lm_has_key, METH_O, "" },
    { "clear", (PyCFunction) t_lm_dict_clear, METH_NOARGS, "" },
    { "firstKey", (PyCFunction) t_lm__getFirstKey, METH_NOARGS, "" },
    { "lastKey", (PyCFunction) t_lm__getLastKey, METH_NOARGS, "" },
    { "previousKey", (PyCFunction) t_lm_previousKey, METH_O, "" },
    { "nextKey", (PyCFunction) t_lm_nextKey, METH_O, "" },
    { NULL, NULL, 0, NULL }
};

static PyGetSetDef t_lm_properties[] = {
    { "_dict",
      (getter) t_lm__getDict,
      NULL, "", NULL },
    { "_aliases",
      (getter) t_lm__getAliases,
      NULL, "", NULL },
    { "_firstKey",
      (getter) t_lm__getFirstKey,
      (setter) t_lm___setFirstKey,
      "", NULL },
    { "_lastKey",
      (getter) t_lm__getLastKey,
      (setter) t_lm___setLastKey,
      "", NULL },
    { NULL, NULL, NULL, NULL, NULL }
};

static PyMappingMethods t_lm_as_mapping = {
    (inquiry) t_lm_dict_length,
    (binaryfunc) t_lm_dict_get,
    (objobjargproc) t_lm_dict_set
};

static PyTypeObject LinkedMapType = {
    PyObject_HEAD_INIT(NULL)
    0,                                /* ob_size */
    "chandlerdb.util.c.CLinkedMap",   /* tp_name */
    sizeof(t_lm),                     /* tp_basicsize */
    0,                                /* tp_itemsize */
    (destructor)t_lm_dealloc,         /* tp_dealloc */
    0,                                /* tp_print */
    0,                                /* tp_getattr */
    0,                                /* tp_setattr */
    0,                                /* tp_compare */
    0,                                /* tp_repr */
    0,                                /* tp_as_number */
    0,                                /* tp_as_sequence */
    &t_lm_as_mapping,                 /* tp_as_mapping */
    0,                                /* tp_hash  */
    0,                                /* tp_call */
    0,                                /* tp_str */
    0,                                /* tp_getattro */
    0,                                /* tp_setattro */
    0,                                /* tp_as_buffer */
    (Py_TPFLAGS_DEFAULT |
     Py_TPFLAGS_BASETYPE |
     Py_TPFLAGS_HAVE_GC),             /* tp_flags */
    "t_lm objects",                   /* tp_doc */
    (traverseproc)t_lm_traverse,      /* tp_traverse */
    (inquiry)t_lm_clear,              /* tp_clear */
    0,                                /* tp_richcompare */
    0,                                /* tp_weaklistoffset */
    0,                                /* tp_iter */
    0,                                /* tp_iternext */
    t_lm_methods,                     /* tp_methods */
    t_lm_members,                     /* tp_members */
    t_lm_properties,                  /* tp_getset */
    0,                                /* tp_base */
    0,                                /* tp_dict */
    0,                                /* tp_descr_get */
    0,                                /* tp_descr_set */
    0,                                /* tp_dictoffset */
    (initproc)t_lm_init,              /* tp_init */
    0,                                /* tp_alloc */
    (newfunc)t_lm_new,                /* tp_new */
};


static void t_lm_dealloc(t_lm *self)
{
    t_lm_clear(self);
    self->ob_type->tp_free((PyObject *) self);
}

static int t_lm_traverse(t_lm *self, visitproc visit, void *arg)
{
    Py_VISIT(self->dict);
    Py_VISIT(self->aliases);
    Py_VISIT(self->head);

    return 0;
}

static int t_lm_clear(t_lm *self)
{
    Py_CLEAR(self->dict);
    Py_CLEAR(self->aliases);
    Py_CLEAR(self->head);

    return 0;
}

static PyObject *t_lm_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    t_lm *self = (t_lm *) type->tp_alloc(type, 0);

    if (self)
    {
        self->dict = PyDict_New();
        self->aliases = PyDict_New();
        self->flags = 0;
        self->count = 0;
    }

    return (PyObject *) self;
}

static int t_lm_init(t_lm *self, PyObject *args, PyObject *kwds)
{
    if (!PyArg_ParseTuple(args, "i", &self->flags))
        return -1;
    else
    {
        PyObject *link = t_link_new(&LinkType, NULL, NULL);
        PyObject *tuple = PyTuple_Pack(2, self, Py_None);
        int init = t_link_init((t_link *) link, tuple, NULL);

        Py_DECREF(tuple);
        if (init < 0)
            return -1;
        
        Py_XDECREF(self->head);
        self->head = link;
    }

    return 0;
}

static PyObject *_t_lm__get(t_lm *self, PyObject *key, int load)
{
    PyObject *link = PyDict_GetItem(self->dict, key);

    if (link == NULL)
    {
        if (load && self->flags & LM_LOAD)
        {
            PyObject *loaded =
                PyObject_CallMethodObjArgs((PyObject *) self, _load_NAME,
                                           key, NULL);

            if (!loaded)
                return NULL;

            if (PyObject_IsTrue(loaded))
                link = PyDict_GetItem(self->dict, key);

            Py_DECREF(loaded);
        }

        if (link == NULL)
        {
            PyErr_SetObject(PyExc_KeyError, key);
            return NULL;
        }
    }

    Py_INCREF(link);
    return link;
}

static PyObject *t_lm__get(t_lm *self, PyObject *args)
{
    PyObject *key, *load = Py_True;

    if (!PyArg_ParseTuple(args, "O|O", &key, &load))
        return NULL;
    else
        return _t_lm__get(self, key, PyObject_IsTrue(load));
}

/* as_mapping */

static int t_lm_dict_length(t_lm *self)
{
    return self->count;
}

static PyObject *t_lm_dict_get(t_lm *self, PyObject *key)
{
    PyObject *value = _t_lm__get(self, key, 1);

    if (!value)
        return NULL;
    else if (!PyObject_TypeCheck(value, &LinkType))
    {
        PyErr_SetObject(PyExc_TypeError, value);
        Py_DECREF(value);

        return NULL;
    }
    else
    {
        t_link *link = (t_link *) value;
        value = t_link_getValue(link, NULL);

        Py_DECREF(link);
        return value;
    }
}

static int t_lm_dict_set(t_lm *self, PyObject *key, PyObject *value)
{
    if (value == NULL)
        return PyDict_DelItem(self->dict, key);
    else
    {
        if (!PyObject_TypeCheck(value, &LinkType))
        {
            PyErr_SetObject(PyExc_TypeError, value);
            return -1;
        }
        else
        {
            t_link *link = (t_link *) value;
            t_link *head = (t_link *) self->head;
            PyObject *previousKey = head->nextKey;

            if (previousKey != Py_None && PyObject_Compare(previousKey, key))
            {
                PyObject *previous = _t_lm__get(self, previousKey, 1);

                if (!previous)
                    return -1;
                else if (!PyObject_TypeCheck(previous, &LinkType))
                {
                    PyErr_SetObject(PyExc_TypeError, previous);
                    Py_DECREF(previous);

                    return -1;
                }
                else
                {
                    int result = _t_link_setNextKey((t_link *) previous,
                                                    key, previousKey);
                    Py_DECREF(previous);
                    if (result < 0)
                        return -1;
                }
            }

            PyDict_SetItem(self->dict, key, value);
            self->count += 1;

            if (previousKey == Py_None || PyObject_Compare(previousKey, key))
            {
                if (_t_link_setPreviousKey(link, previousKey, key) < 0)
                    return -1;
            }

            if (_t_link_setNextKey(link, Py_None, key) < 0)
                return -1;

            if (link->alias != Py_None)
                PyDict_SetItem(self->aliases, link->alias, key);

            return 0;
        }
    }
}


static PyObject *t_lm_get(t_lm *self, PyObject *args)
{
    PyObject *key, *defaultValue = Py_None;

    if (!PyArg_ParseTuple(args, "O|O", &key, &defaultValue))
        return NULL;
    else
    {
        PyObject *value = PyDict_GetItem(self->dict, key);

        if (!value)
            value = defaultValue;

        Py_INCREF(value);
        return value;
    }
}

static PyObject *t_lm_has_key(t_lm *self, PyObject *key)
{
    if (PyDict_Contains(self->dict, key))
        Py_RETURN_TRUE;

    Py_RETURN_FALSE;
}

static PyObject *t_lm_dict_clear(t_lm *self, PyObject *args)
{
    PyDict_Clear(self->dict);
    PyDict_Clear(self->aliases);

    Py_RETURN_NONE;
}


static PyObject *t_lm_previousKey(t_lm *self, PyObject *key)
{
    PyObject *link = _t_lm__get(self, key, 1);

    if (!link)
        return NULL;
    else if (!PyObject_TypeCheck(link, &LinkType))
    {
        PyErr_SetObject(PyExc_TypeError, link);
        return NULL;
    }
    else
    {
        PyObject *previousKey = ((t_link *) link)->previousKey;

        Py_INCREF(previousKey);
        Py_DECREF(link);

        return previousKey;
    }
}

static PyObject *t_lm_nextKey(t_lm *self, PyObject *key)
{
    PyObject *link = _t_lm__get(self, key, 1);

    if (!link)
        return NULL;
    else if (!PyObject_TypeCheck(link, &LinkType))
    {
        PyErr_SetObject(PyExc_TypeError, link);
        return NULL;
    }
    else
    {
        PyObject *nextKey = ((t_link *) link)->nextKey;

        Py_INCREF(nextKey);
        Py_DECREF(link);

        return nextKey;
    }
}


/* _dict property */

static PyObject *t_lm__getDict(t_lm *self, void *data)
{
    PyObject *dict = self->dict;

    Py_INCREF(dict);
    return dict;
}


/* _aliases property */

static PyObject *t_lm__getAliases(t_lm *self, void *data)
{
    PyObject *aliases = self->aliases;

    Py_INCREF(aliases);
    return aliases;
}


/* _firstKey property */

static PyObject *t_lm__getFirstKey(t_lm *self, void *data)
{
    t_link *head = (t_link *) self->head;
    PyObject *key = head->previousKey;

    Py_INCREF(key);
    return key;
}

static int t_lm___setFirstKey(t_lm *self, PyObject *arg, void *data)
{
    t_link *head = (t_link *) self->head;
    PyObject *key = head->previousKey;

    Py_INCREF(arg); Py_XDECREF(key);
    head->previousKey = arg;

    return 0;
}


/* _lastKey property */

static PyObject *t_lm__getLastKey(t_lm *self, void *data)
{
    t_link *head = (t_link *) self->head;
    PyObject *key = head->nextKey;

    Py_INCREF(key);
    return key;
}

static int t_lm___setLastKey(t_lm *self, PyObject *arg, void *data)
{
    t_link *head = (t_link *) self->head;
    PyObject *key = head->nextKey;

    Py_INCREF(arg); Py_XDECREF(key);
    head->nextKey = arg;

    return 0;
}


void _init_linkedmap(PyObject *m)
{
    if (PyType_Ready(&LinkedMapType) >= 0 && PyType_Ready(&LinkType) >= 0)
    {
        if (m)
        {
            PyObject *dict = LinkedMapType.tp_dict;

            Py_INCREF(&LinkedMapType);
            PyModule_AddObject(m, "CLinkedMap", (PyObject *) &LinkedMapType);
            CLinkedMap = &LinkedMapType;

            PyDict_SetItemString_Int(dict, "NEW", LM_NEW);
            PyDict_SetItemString_Int(dict, "LOAD", LM_LOAD);

            Py_INCREF(&LinkType);
            PyModule_AddObject(m, "CLink", (PyObject *) &LinkType);
            CLink = &LinkType;

            _load_NAME = PyString_FromString("_load");
            linkChanged_NAME = PyString_FromString("linkChanged");
            view_NAME = PyString_FromString("view");
        }
    }
}
