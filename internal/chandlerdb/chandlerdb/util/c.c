
/*
 * The C util types module
 *
 * Copyright (c) 2003-2005 Open Source Applications Foundation
 * License at http://osafoundation.org/Chandler_0.1_license_terms.htm
 */


#include <Python.h>
#include "structmember.h"

#include "c.h"

PyTypeObject *UUID = NULL;
PyTypeObject *SingleRef = NULL;
PyTypeObject *Key = NULL;
PyTypeObject *Cipher = NULL;
PyTypeObject *CLinkedMap = NULL;
PyTypeObject *CLink = NULL;
PyTypeObject *CPoint = NULL;
PyTypeObject *CNode = NULL;
PyTypeObject *SkipList = NULL;


static PyObject *isuuid(PyObject *self, PyObject *obj)
{
    if (PyObject_TypeCheck(obj, UUID))
        Py_RETURN_TRUE;

    Py_RETURN_FALSE;
}

static PyObject *issingleref(PyObject *self, PyObject *obj)
{
    if (PyObject_TypeCheck(obj, SingleRef))
        Py_RETURN_TRUE;

    Py_RETURN_FALSE;
}

static PyObject *hash(PyObject *self, PyObject *args)
{
    unsigned char *data;
    unsigned int len = 0;

    if (!PyArg_ParseTuple(args, "s#", &data, &len))
        return 0;

    return PyInt_FromLong(hash_bytes(data, len));
}

static PyObject *combine(PyObject *self, PyObject *args)
{
    unsigned long h0, h1;

    if (!PyArg_ParseTuple(args, "ll", &h0, &h1))
        return 0;

    return PyInt_FromLong(combine_longs(h0, h1));
}


static PyMethodDef c_funcs[] = {
    { "isuuid", (PyCFunction) isuuid, METH_O, "isinstance(UUID)" },
    { "issingleref", (PyCFunction) issingleref, METH_O, "isinstance(SingleRef)" },
    { "_hash", (PyCFunction) hash, METH_VARARGS, "hash bytes" },
    { "_combine", (PyCFunction) combine, METH_VARARGS, "combine two hashes" },
#ifdef WINDOWS
    { "openHFILE", (PyCFunction) openHFILE, METH_VARARGS, "open HFILE" },
    { "closeHFILE", (PyCFunction) closeHFILE, METH_VARARGS, "close HFILE" },
    { "lockHFILE", (PyCFunction) lockHFILE, METH_VARARGS,
      "lock, unlock, upgrade or downgrade lock on an HFILE" },
#endif
    { NULL, NULL, 0, NULL }
};


void PyDict_SetItemString_Int(PyObject *dict, char *key, int value)
{
    PyObject *pyValue = PyInt_FromLong(value);

    PyDict_SetItemString(dict, key, pyValue);
    Py_DECREF(pyValue);
}


void initc(void)
{
    PyObject *m = Py_InitModule3("c", c_funcs, "C util types module");

    _init_uuid(m);
    _init_singleref(m);
    _init_rijndael(m);
    _init_linkedmap(m);
    _init_skiplist(m);
#ifdef WINDOWS
    _init_lock(m);
#endif
}    
