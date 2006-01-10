
/*
 * The DBEnv C type module
 *
 * Copyright (c) 2003-2005 Open Source Applications Foundation
 * License at http://osafoundation.org/Chandler_0.1_license_terms.htm
 */


#include <Python.h>
#include "structmember.h"

#include "c.h"

static void t_env_dealloc(t_env *self);
static PyObject *t_env_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static int t_env_init(t_env *self, PyObject *args, PyObject *kwds);

static PyObject *t_env_open(t_env *self, PyObject *args);
static PyObject *t_env_close(t_env *self, PyObject *args);
static PyObject *t_env_txn_begin(t_env *self, PyObject *args);
static PyObject *t_env_txn_checkpoint(t_env *self, PyObject *args);
static PyObject *t_env_set_flags(t_env *self, PyObject *args);
static PyObject *t_env_get_flags(t_env *self, PyObject *args);
static PyObject *t_env_get_open_flags(t_env *self, PyObject *args);
static PyObject *t_env_get_encrypt_flags(t_env *self, PyObject *args);
static PyObject *t_env_get_home(t_env *self, PyObject *args);
static PyObject *t_env_set_encrypt(t_env *self, PyObject *args);
static PyObject *t_env_log_archive(t_env *self, PyObject *args);
static PyObject *t_env_lock_detect(t_env *self, PyObject *args);
static PyObject *t_env_lock_id(t_env *self, PyObject *args);
static PyObject *t_env_lock_id_free(t_env *self, PyObject *args);
static PyObject *t_env_lock_get(t_env *self, PyObject *args);
static PyObject *t_env_lock_put(t_env *self, PyObject *args);

static PyObject *t_env_get_lk_detect(t_env *self, void *data);
static int t_env_set_lk_detect(t_env *self, PyObject *value, void *data);
static PyObject *t_env_get_lk_max_locks(t_env *self, void *data);
static int t_env_set_lk_max_locks(t_env *self, PyObject *value, void *data);
static PyObject *t_env_get_lk_max_lockers(t_env *self, void *data);
static int t_env_set_lk_max_lockers(t_env *self, PyObject *value, void *data);
static PyObject *t_env_get_lk_max_objects(t_env *self, void *data);
static int t_env_set_lk_max_objects(t_env *self, PyObject *value, void *data);
static PyObject *t_env_get_cachesize(t_env *self, void *data);
static int t_env_set_cachesize(t_env *self, PyObject *value, void *data);


static PyMemberDef t_env_members[] = {
    { NULL, 0, 0, 0, NULL }
};

static PyMethodDef t_env_methods[] = {
    { "open", (PyCFunction) t_env_open, METH_VARARGS, NULL },
    { "close", (PyCFunction) t_env_close, METH_VARARGS, NULL },
    { "txn_begin", (PyCFunction) t_env_txn_begin, METH_VARARGS, NULL },
    { "txn_checkpoint", (PyCFunction) t_env_txn_checkpoint, METH_VARARGS, NULL },
    { "log_archive", (PyCFunction) t_env_log_archive, METH_VARARGS, NULL },
    { "set_flags", (PyCFunction) t_env_set_flags, METH_VARARGS, NULL },
    { "get_flags", (PyCFunction) t_env_get_flags, METH_NOARGS, NULL },
    { "get_open_flags", (PyCFunction) t_env_get_open_flags, METH_NOARGS, NULL },
    { "get_encrypt_flags", (PyCFunction) t_env_get_encrypt_flags, METH_NOARGS, NULL },
    { "get_home", (PyCFunction) t_env_get_flags, METH_NOARGS, NULL },
    { "set_encrypt", (PyCFunction) t_env_set_encrypt, METH_VARARGS, NULL },
    { "lock_detect", (PyCFunction) t_env_lock_detect, METH_VARARGS, NULL },
    { "lock_id", (PyCFunction) t_env_lock_id, METH_NOARGS, NULL },
    { "lock_id_free", (PyCFunction) t_env_lock_id_free, METH_O, NULL },
    { "lock_get", (PyCFunction) t_env_lock_get, METH_VARARGS, NULL },
    { "lock_put", (PyCFunction) t_env_lock_put, METH_O, NULL },
    { NULL, NULL, 0, NULL }
};

static PyGetSetDef t_env_properties[] = {
    { "lk_detect",
      (getter) t_env_get_lk_detect, (setter) t_env_set_lk_detect,
      "deadlock detector", NULL },
    { "lk_max_locks",
      (getter) t_env_get_lk_max_locks, (setter) t_env_set_lk_max_locks,
      "maximum number of locks", NULL },
    { "lk_max_lockers",
      (getter) t_env_get_lk_max_lockers, (setter) t_env_set_lk_max_lockers,
      "maximum number of locking entities", NULL },
    { "lk_max_objects",
      (getter) t_env_get_lk_max_objects, (setter) t_env_set_lk_max_objects,
      "maximum number of locked objects", NULL },
    { "flags",
      (getter) t_env_get_flags, (setter) NULL,
      "environment configuration flags", NULL },
    { "open_flags",
      (getter) t_env_get_open_flags, (setter) NULL,
      "environment open flags", NULL },
    { "encrypt_flags",
      (getter) t_env_get_encrypt_flags, (setter) NULL,
      "environment encrypt flags", NULL },
    { "home",
      (getter) t_env_get_home, (setter) NULL,
      "environment home", NULL },
    { "cachesize",
      (getter) t_env_get_cachesize, (setter) t_env_set_cachesize,
      "size of shared memory buffer pool", NULL },
    { NULL, NULL, NULL, NULL, NULL }
};

static PyTypeObject DBEnvType = {
    PyObject_HEAD_INIT(NULL)
    0,                                               /* ob_size */
    "chandlerdb.persistence.c.DBEnv",                /* tp_name */
    sizeof(t_env),                                   /* tp_basicsize */
    0,                                               /* tp_itemsize */
    (destructor)t_env_dealloc,                       /* tp_dealloc */
    0,                                               /* tp_print */
    0,                                               /* tp_getattr */
    0,                                               /* tp_setattr */
    0,                                               /* tp_compare */
    0,                                               /* tp_repr */
    0,                                               /* tp_as_number */
    0,                                               /* tp_as_sequence */
    0,                                               /* tp_as_mapping */
    0,                                               /* tp_hash  */
    0,                                               /* tp_call */
    0,                                               /* tp_str */
    0,                                               /* tp_getattro */
    0,                                               /* tp_setattro */
    0,                                               /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,                              /* tp_flags */
    "C DBEnv type",                                  /* tp_doc */
    0,                                               /* tp_traverse */
    0,                                               /* tp_clear */
    0,                                               /* tp_richcompare */
    0,                                               /* tp_weaklistoffset */
    0,                                               /* tp_iter */
    0,                                               /* tp_iternext */
    t_env_methods,                                   /* tp_methods */
    t_env_members,                                   /* tp_members */
    t_env_properties,                                /* tp_getset */
    0,                                               /* tp_base */
    0,                                               /* tp_dict */
    0,                                               /* tp_descr_get */
    0,                                               /* tp_descr_set */
    0,                                               /* tp_dictoffset */
    (initproc)t_env_init,                            /* tp_init */
    0,                                               /* tp_alloc */
    (newfunc)t_env_new,                              /* tp_new */
};


static int _t_env_close(t_env *self, int flags)
{
    if (self->db_env)
    {
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->close(self->db_env, flags);
        Py_END_ALLOW_THREADS;

        if (err)
        {
            raiseDBError(err);
            return -1;
        }

        self->db_env = NULL;
    }

    return 0;
}

static void t_env_dealloc(t_env *self)
{
    _t_env_close(self, 0);
    self->ob_type->tp_free((PyObject *) self);
}

static PyObject *t_env_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    return type->tp_alloc(type, 0);
}

static int t_env_init(t_env *self, PyObject *args, PyObject *kwds)
{
    int flags = 0;

    if (!PyArg_ParseTuple(args, "|i", &flags))
        return -1;
    else
    {
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = db_env_create(&self->db_env, flags);
        Py_END_ALLOW_THREADS;

        if (err)
        {
            raiseDBError(err);
            return -1;
        }

        self->db_env->app_private = self;
    }

    return 0;
}

static PyObject *t_env_open(t_env *self, PyObject *args)
{
    char *db_home;
    int flags = 0, mode = 0;

    if (!self->db_env)
        return raiseDBError(EINVAL);

    if (!PyArg_ParseTuple(args, "z|ii", &db_home, &flags, &mode))
        return NULL;

    {
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->open(self->db_env, db_home, flags, mode);
        Py_END_ALLOW_THREADS;

        if (err)
            return raiseDBError(err);
        
        Py_RETURN_NONE;
    }
}

static PyObject *t_env_close(t_env *self, PyObject *args)
{
    int flags = 0;

    if (!PyArg_ParseTuple(args, "|i", &flags))
        return NULL;

    if (_t_env_close(self, flags) < 0)
        return NULL;
        
    Py_RETURN_NONE;
}

static PyObject *t_env_txn_begin(t_env *self, PyObject *args)
{
    PyObject *parent = Py_None;
    int flags = 0;

    if (!self->db_env)
        return raiseDBError(EINVAL);

    if (!PyArg_ParseTuple(args, "|Oi", &parent, &flags))
        return NULL;

    if (parent != Py_None && !PyObject_TypeCheck(parent, CDBTxn))
    {
        PyErr_SetObject(PyExc_TypeError, parent);
        return NULL;
    }

    {
        PyObject *txn = t_txn_new(CDBTxn, NULL, NULL);

        if (_t_txn_init((t_txn *) txn, self->db_env,
                        parent == Py_None ? NULL : ((t_txn *) parent)->txn,
                        flags) < 0)
        {
            Py_DECREF(txn);
            return NULL;
        }

        return txn;
    }
}

static PyObject *t_env_txn_checkpoint(t_env *self, PyObject *args)
{
    u_int32_t kbyte = 0, minutes = 0, flags = 0;

    if (!self->db_env)
        return raiseDBError(EINVAL);

    if (!PyArg_ParseTuple(args, "|iii", &kbyte, &minutes, &flags))
        return NULL;

    {
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->txn_checkpoint(self->db_env, kbyte, minutes, flags);
        Py_END_ALLOW_THREADS;

        if (err)
            return raiseDBError(err);

        Py_RETURN_NONE;
    }
}

static PyObject *t_env_log_archive(t_env *self, PyObject *args)
{
    int flags = 0;

    if (!self->db_env)
        return raiseDBError(EINVAL);

    if (!PyArg_ParseTuple(args, "|i", &flags))
        return NULL;

    {
        char **list = NULL;
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->log_archive(self->db_env, &list, flags);
        Py_END_ALLOW_THREADS;

        if (err)
            return raiseDBError(err);

        {
            PyObject *strings = PyList_New(0);

            if (list)
            {
                char **name;

                for (name = list; *name; name++) {
                    PyObject *string = PyString_FromString(*name);

                    PyList_Append(strings, string);
                    Py_DECREF(string);
                }

                free(list);
            }

            return strings;
        }
    }
}

static PyObject *t_env_set_flags(t_env *self, PyObject *args)
{
    int flags, on;

    if (!self->db_env)
        return raiseDBError(EINVAL);

    if (!PyArg_ParseTuple(args, "ii", &flags, &on))
        return NULL;

    {
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->set_flags(self->db_env, flags, on);
        Py_END_ALLOW_THREADS;

        if (err)
            return raiseDBError(err);

        Py_RETURN_NONE;
    }
}

static PyObject *t_env_get_flags(t_env *self, PyObject *args)
{
    if (!self->db_env)
        return raiseDBError(EINVAL);

    {
        u_int32_t flags;
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->get_flags(self->db_env, &flags);
        Py_END_ALLOW_THREADS;

        if (err)
            return raiseDBError(err);

        return PyInt_FromLong(flags);
    }
}

static PyObject *t_env_get_open_flags(t_env *self, PyObject *args)
{
    if (!self->db_env)
        return raiseDBError(EINVAL);

    {
        u_int32_t flags;
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->get_open_flags(self->db_env, &flags);
        Py_END_ALLOW_THREADS;

        if (err)
            return raiseDBError(err);

        return PyInt_FromLong(flags);
    }
}

static PyObject *t_env_get_encrypt_flags(t_env *self, PyObject *args)
{
    if (!self->db_env)
        return raiseDBError(EINVAL);

    {
        u_int32_t flags;
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->get_encrypt_flags(self->db_env, &flags);
        Py_END_ALLOW_THREADS;

        if (err)
            return raiseDBError(err);

        return PyInt_FromLong(flags);
    }
}

static PyObject *t_env_get_home(t_env *self, PyObject *args)
{
    if (!self->db_env)
        return raiseDBError(EINVAL);

    {
        const char *home;
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->get_home(self->db_env, &home);
        Py_END_ALLOW_THREADS;

        if (err)
            return raiseDBError(err);

        if (home)
            return PyString_FromString(home);

        Py_RETURN_NONE;
    }
}

static PyObject *t_env_set_encrypt(t_env *self, PyObject *args)
{
    const char *passwd;
    int flags = 0;

    if (!self->db_env)
        return raiseDBError(EINVAL);

    if (!PyArg_ParseTuple(args, "s|i", &passwd, &flags))
        return NULL;

    {
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->set_encrypt(self->db_env, passwd, flags);
        Py_END_ALLOW_THREADS;

        if (err)
            return raiseDBError(err);

        Py_RETURN_NONE;
    }
}

static PyObject *t_env_lock_detect(t_env *self, PyObject *args)
{
    int type = DB_LOCK_DEFAULT;

    if (!self->db_env)
        return raiseDBError(EINVAL);

    if (!PyArg_ParseTuple(args, "|i", &type))
        return NULL;

    {
        int aborted;
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->lock_detect(self->db_env, 0, type, &aborted);
        Py_END_ALLOW_THREADS;

        if (err)
            return raiseDBError(err);

        return PyInt_FromLong(aborted);
    }
}

static PyObject *t_env_lock_id(t_env *self, PyObject *args)
{
    if (!self->db_env)
        return raiseDBError(EINVAL);

    {
        u_int32_t id;
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->lock_id(self->db_env, &id);
        Py_END_ALLOW_THREADS;

        if (err)
            return raiseDBError(err);

        return PyInt_FromLong(id);
    }
}

static PyObject *t_env_lock_id_free(t_env *self, PyObject *value)
{
    int id = PyInt_AsLong(value);

    if (PyErr_Occurred())
        return NULL;

    if (!self->db_env)
        return raiseDBError(EINVAL);

    {
        int err;

        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->lock_id_free(self->db_env, id);
        Py_END_ALLOW_THREADS;

        if (err)
            return raiseDBError(err);

        Py_RETURN_NONE;
    }
}

static PyObject *t_env_lock_get(t_env *self, PyObject *args)
{
    int id, mode;
    DBT data;
    int flags = 0;

    if (!self->db_env)
        return raiseDBError(EINVAL);

    if (!PyArg_ParseTuple(args, "is#i|i", &id, &data.data, &data.size,
                          &mode, &flags))
        return NULL;

    {
        PyObject *lock = t_lock_new(CDBLock, NULL, NULL);

        if (_t_lock_init((t_lock *) lock, self, id, &data, mode, flags) < 0)
        {
            Py_DECREF(lock);
            return NULL;
        }

        return lock;
    }
}

static PyObject *t_env_lock_put(t_env *self, PyObject *value)
{
    if (!self->db_env)
        return raiseDBError(EINVAL);

    if (!PyObject_TypeCheck(value, CDBLock))
    {
        PyErr_SetObject(PyExc_TypeError, value);
        return NULL;
    }

    if (_t_lock_put((t_lock *) value) < 0)
        return NULL;

    Py_RETURN_NONE;
}


/* lk_detect */

static PyObject *t_env_get_lk_detect(t_env *self, void *data)
{
    u_int32_t detect;
    int err;

    if (self->db_env)
    {
        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->get_lk_detect(self->db_env, &detect);
        Py_END_ALLOW_THREADS;
    }
    else
        err = EINVAL;

    if (err)
        return raiseDBError(err);

    return PyInt_FromLong(detect);
}

static int t_env_set_lk_detect(t_env *self, PyObject *value, void *data)
{
    u_int32_t detect = (u_int32_t) PyInt_AsLong(value);
    int err;

    if (PyErr_Occurred())
        return -1;

    if (self->db_env)
    {
        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->set_lk_detect(self->db_env, detect);
        Py_END_ALLOW_THREADS;
    }
    else
        err = EINVAL;

    if (err)
    {
        raiseDBError(err);
        return -1;
    }

    return 0;
}


/* lk_max_locks */

static PyObject *t_env_get_lk_max_locks(t_env *self, void *data)
{
    u_int32_t max_locks;
    int err;

    if (self->db_env)
    {
        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->get_lk_max_locks(self->db_env, &max_locks);
        Py_END_ALLOW_THREADS;
    }
    else
        err = EINVAL;

    if (err)
        return raiseDBError(err);

    return PyInt_FromLong(max_locks);
}

static int t_env_set_lk_max_locks(t_env *self, PyObject *value, void *data)
{
    u_int32_t max_locks = (u_int32_t) PyInt_AsLong(value);
    int err;

    if (PyErr_Occurred())
        return -1;

    if (self->db_env)
    {
        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->set_lk_max_locks(self->db_env, max_locks);
        Py_END_ALLOW_THREADS;
    }
    else
        err = EINVAL;

    if (err)
    {
        raiseDBError(err);
        return -1;
    }

    return 0;
}


/* lk_max_lockers */

static PyObject *t_env_get_lk_max_lockers(t_env *self, void *data)
{
    u_int32_t max_lockers;
    int err;

    if (self->db_env)
    {
        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->get_lk_max_lockers(self->db_env, &max_lockers);
        Py_END_ALLOW_THREADS;
    }
    else
        err = EINVAL;

    if (err)
        return raiseDBError(err);

    return PyInt_FromLong(max_lockers);
}

static int t_env_set_lk_max_lockers(t_env *self, PyObject *value, void *data)
{
    u_int32_t max_lockers = (u_int32_t) PyInt_AsLong(value);
    int err;

    if (PyErr_Occurred())
        return -1;

    if (self->db_env)
    {
        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->set_lk_max_lockers(self->db_env, max_lockers);
        Py_END_ALLOW_THREADS;
    }
    else
        err = EINVAL;

    if (err)
    {
        raiseDBError(err);
        return -1;
    }

    return 0;
}


/* lk_max_objects */

static PyObject *t_env_get_lk_max_objects(t_env *self, void *data)
{
    u_int32_t max_objects;
    int err;

    if (self->db_env)
    {
        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->get_lk_max_objects(self->db_env, &max_objects);
        Py_END_ALLOW_THREADS;
    }
    else
        err = EINVAL;

    if (err)
        return raiseDBError(err);

    return PyInt_FromLong(max_objects);
}

static int t_env_set_lk_max_objects(t_env *self, PyObject *value, void *data)
{
    u_int32_t max_objects = (u_int32_t) PyInt_AsLong(value);
    int err;

    if (PyErr_Occurred())
        return -1;

    if (self->db_env)
    {
        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->set_lk_max_objects(self->db_env, max_objects);
        Py_END_ALLOW_THREADS;
    }
    else
        err = EINVAL;

    if (err)
    {
        raiseDBError(err);
        return -1;
    }

    return 0;
}


/* cachesize */

static PyObject *t_env_get_cachesize(t_env *self, void *data)
{
    u_int32_t gbytes, bytes;
    int err, ncache;

    if (self->db_env)
    {
        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->get_cachesize(self->db_env,
                                          &gbytes, &bytes, &ncache);
        Py_END_ALLOW_THREADS;
    }
    else
        err = EINVAL;

    if (err)
        return raiseDBError(err);

    return Py_BuildValue("(iii)", gbytes, bytes, ncache);
}

static int t_env_set_cachesize(t_env *self, PyObject *value, void *data)
{
    u_int32_t gbytes, bytes;
    int err, ncache;

    if (!PyArg_ParseTuple(value, "IIi", &gbytes, &bytes, &ncache))
        return -1;

    if (self->db_env)
    {
        Py_BEGIN_ALLOW_THREADS;
        err = self->db_env->set_cachesize(self->db_env, gbytes, bytes, ncache);
        Py_END_ALLOW_THREADS;
    }
    else
        err = EINVAL;

    if (err)
    {
        raiseDBError(err);
        return -1;
    }

    return 0;
}


void _init_env(PyObject *m)
{
    if (PyType_Ready(&DBEnvType) >= 0)
    {
        if (m)
        {
            PyObject *dict = DBEnvType.tp_dict;

            Py_INCREF(&DBEnvType);
            PyModule_AddObject(m, "DBEnv", (PyObject *) &DBEnvType);

            CDBEnv = &DBEnvType;

            /* flags */
            SET_DB_INT(dict, DB_RPCCLIENT);
            SET_DB_INT(dict, DB_READ_COMMITTED);
            SET_DB_INT(dict, DB_READ_UNCOMMITTED);
            SET_DB_INT(dict, DB_TXN_NOSYNC);
            SET_DB_INT(dict, DB_TXN_WRITE_NOSYNC);
            SET_DB_INT(dict, DB_TXN_NOWAIT);
            SET_DB_INT(dict, DB_TXN_SYNC);
            SET_DB_INT(dict, DB_AUTO_COMMIT);
            SET_DB_INT(dict, DB_CDB_ALLDB);
            SET_DB_INT(dict, DB_DIRECT_DB);
            SET_DB_INT(dict, DB_DIRECT_LOG);
            SET_DB_INT(dict, DB_DSYNC_DB);
            SET_DB_INT(dict, DB_DSYNC_LOG);
            SET_DB_INT(dict, DB_LOG_AUTOREMOVE);
            SET_DB_INT(dict, DB_LOG_INMEMORY);
            SET_DB_INT(dict, DB_NOLOCKING);
            SET_DB_INT(dict, DB_NOMMAP);
            SET_DB_INT(dict, DB_NOPANIC);
            SET_DB_INT(dict, DB_OVERWRITE);
            SET_DB_INT(dict, DB_PANIC_ENVIRONMENT);
            SET_DB_INT(dict, DB_REGION_INIT);
            SET_DB_INT(dict, DB_TIME_NOTGRANTED);
            SET_DB_INT(dict, DB_YIELDCPU);
            SET_DB_INT(dict, DB_RECOVER);
            SET_DB_INT(dict, DB_RECOVER_FATAL);
            SET_DB_INT(dict, DB_USE_ENVIRON);
            SET_DB_INT(dict, DB_USE_ENVIRON_ROOT);
            SET_DB_INT(dict, DB_CREATE);
            SET_DB_INT(dict, DB_LOCKDOWN);
            SET_DB_INT(dict, DB_PRIVATE);
            SET_DB_INT(dict, DB_REGISTER);
            SET_DB_INT(dict, DB_SYSTEM_MEM);
            SET_DB_INT(dict, DB_THREAD);
            SET_DB_INT(dict, DB_ENCRYPT_AES);
            SET_DB_INT(dict, DB_FORCE);

            SET_DB_INT(dict, DB_INIT_CDB);
            SET_DB_INT(dict, DB_INIT_MPOOL);
            SET_DB_INT(dict, DB_INIT_LOCK);
            SET_DB_INT(dict, DB_INIT_LOG);
            SET_DB_INT(dict, DB_INIT_REP);
            SET_DB_INT(dict, DB_INIT_TXN);

            SET_DB_INT(dict, DB_ARCH_ABS);
            SET_DB_INT(dict, DB_ARCH_DATA);
            SET_DB_INT(dict, DB_ARCH_LOG);
            SET_DB_INT(dict, DB_ARCH_REMOVE);

            SET_DB_INT(dict, DB_LOCK_DEFAULT);
            SET_DB_INT(dict, DB_LOCK_RANDOM);
            SET_DB_INT(dict, DB_LOCK_EXPIRE);
            SET_DB_INT(dict, DB_LOCK_MAXLOCKS);
            SET_DB_INT(dict, DB_LOCK_MAXWRITE);
            SET_DB_INT(dict, DB_LOCK_MINLOCKS);
            SET_DB_INT(dict, DB_LOCK_MINWRITE);
            SET_DB_INT(dict, DB_LOCK_OLDEST);
            SET_DB_INT(dict, DB_LOCK_YOUNGEST);

            SET_DB_INT(dict, DB_LOCK_READ);
            SET_DB_INT(dict, DB_LOCK_WRITE);
            SET_DB_INT(dict, DB_LOCK_IWRITE);
            SET_DB_INT(dict, DB_LOCK_IREAD);
            SET_DB_INT(dict, DB_LOCK_IWR);
        }
    }
}
