# Sample application: Django Admin + Popyka

This sample app show how to capture the DB changes of a simple Django app.

To access to the services use the following URLs:

* Django: http://localhost:8081/admin/ (`admin`:`admin`)
* Kowl / Red Panda Console: http://localhost:8082/

To launch the services & the demo app:

    $ cd samples/django-admin               # cd to this directory
    $ docker compose build                  # to build the containers
    $ docker compose up -d                  # launch pgsql+kafka+redpanda+popyka
    $ docker compose logs demo-popyka -f    # to see the CDC working :)

It might happen that Kafka or PostgreSql takes some time to start. You can check if all services
are up with `docker compose ps --services`.

```shell
$ docker compose ps --services
demo-db
demo-django-admin
demo-kafka
demo-kowl
demo-popyka
```

If any of the services is not up, you can run `docker compose up -d` again.

# Demo

Let's see the output of 2 common actions:

* Sign in into Django
* Update the admin user


### Sign in into Django

For example, when sign in into Django with the `admin` user, you should get something like
in the output of `demo-popyka`:

1. Django executing an `INSERT` (`"action": "I"`) on the table `django_session`:

```
INFO:popyka.builtin.processors:LogChangeProcessor: change: {
    "action": "I",
    "columns": [
        {
            "name": "session_key",
            "type": "character varying(40)",
            "value": "fdsywhfjl2we7bi54qtxg2tmif7f5l3z"
        },
        {
            "name": "session_data",
            "type": "text",
            "value": "e30:1rvgko:kE2Yi3ti-KMfmRzd9qWxCj6n39wNq0H3ZwMFJjLzf6g"
        },
        {
            "name": "expire_date",
            "type": "timestamp with time zone",
            "value": "2024-04-27 17:01:26.038507+00"
        }
    ],
    "schema": "public",
    "table": "django_session"
}
```


2. Django executing an `UPDATE` (`"action": "U"`) on the table `auth_user`:

```
INFO:popyka.builtin.processors:LogChangeProcessor: change: {
    "action": "U",
    "columns": [
        {
            "name": "id",
            "type": "integer",
            "value": 1
        },
        {
            "name": "password",
            "type": "character varying(128)",
            "value": "pbkdf2_sha256$720000$jMLYjPGec8m1G7BfxXehCV$U8Ib0qOP8T8t3Akl/aVS6JXiiQsjtc+YIUdpzAaQ1OY="
        },
        {
            "name": "last_login",
            "type": "timestamp with time zone",
            "value": "2024-04-13 17:01:26.039737+00"
        },
        {
            "name": "is_superuser",
            "type": "boolean",
            "value": true
        },
        {
            "name": "username",
            "type": "character varying(150)",
            "value": "admin"
        },
        {
            "name": "first_name",
            "type": "character varying(150)",
            "value": ""
        },
        {
            "name": "last_name",
            "type": "character varying(150)",
            "value": ""
        },
        {
            "name": "email",
            "type": "character varying(254)",
            "value": "admin@example.com"
        },
        {
            "name": "is_staff",
            "type": "boolean",
            "value": true
        },
        {
            "name": "is_active",
            "type": "boolean",
            "value": true
        },
        {
            "name": "date_joined",
            "type": "timestamp with time zone",
            "value": "2024-04-11 19:42:12+00"
        }
    ],
    "identity": [
        {
            "name": "id",
            "type": "integer",
            "value": 1
        }
    ],
    "schema": "public",
    "table": "auth_user"
}
```

3. Django executing an `UPDATE` (`"action": "U"`) on the table `django_session`:

```
INFO:popyka.builtin.processors:LogChangeProcessor: change: {
    "action": "U",
    "columns": [
        {
            "name": "session_key",
            "type": "character varying(40)",
            "value": "fdsywhfjl2we7bi54qtxg2tmif7f5l3z"
        },
        {
            "name": "session_data",
            "type": "text",
            "value": ".eJxVjDsOwjAQBe_iGlnrP1DScwZr7V3jALKlOKkQd4dIKaB9M_NeIuK61LgOnuNE4iyUOPxuCfOD2wboju3WZe5tmackN0XudMhrJ35edvfvoOKo3xoU6AQOTrno7DzlYpFZG08ulGILaccJEUxg9DoEBFTWBqOOlLzHIt4f7iY4Rw:1rvgko:gHXFId9PSlKpSAUPEbO_rR6jl3DSwQu9c_qBAyuP0iY"
        },
        {
            "name": "expire_date",
            "type": "timestamp with time zone",
            "value": "2024-04-27 17:01:26.041355+00"
        }
    ],
    "identity": [
        {
            "name": "session_key",
            "type": "character varying(40)",
            "value": "fdsywhfjl2we7bi54qtxg2tmif7f5l3z"
        }
    ],
    "schema": "public",
    "table": "django_session"
}
```


### Update the admin user

If you update the `admin` user, you'll see something like:

1. Django executing an `UPDATE` (`"action": "U"`) on the table `auth_user`:

```
INFO:popyka.builtin.processors:LogChangeProcessor: change: {
    "action": "U",
    "columns": [
        {
            "name": "id",
            "type": "integer",
            "value": 1
        },
        {
            "name": "password",
            "type": "character varying(128)",
            "value": "pbkdf2_sha256$720000$jMLYjPGec8m1G7BfxXehCV$U8Ib0qOP8T8t3Akl/aVS6JXiiQsjtc+YIUdpzAaQ1OY="
        },
        {
            "name": "last_login",
            "type": "timestamp with time zone",
            "value": "2024-04-13 17:01:26+00"
        },
        {
            "name": "is_superuser",
            "type": "boolean",
            "value": true
        },
        {
            "name": "username",
            "type": "character varying(150)",
            "value": "admin"
        },
        {
            "name": "first_name",
            "type": "character varying(150)",
            "value": ""
        },
        {
            "name": "last_name",
            "type": "character varying(150)",
            "value": ""
        },
        {
            "name": "email",
            "type": "character varying(254)",
            "value": "admin@example.com"
        },
        {
            "name": "is_staff",
            "type": "boolean",
            "value": true
        },
        {
            "name": "is_active",
            "type": "boolean",
            "value": true
        },
        {
            "name": "date_joined",
            "type": "timestamp with time zone",
            "value": "2024-04-11 19:42:12+00"
        }
    ],
    "identity": [
        {
            "name": "id",
            "type": "integer",
            "value": 1
        }
    ],
    "schema": "public",
    "table": "auth_user"
}
```

2. Django executing an `INSERT` (`"action": "i"`) on the table `django_admin_log`:

```
INFO:popyka.builtin.processors:LogChangeProcessor: change: {
    "action": "I",
    "columns": [
        {
            "name": "id",
            "type": "integer",
            "value": 37
        },
        {
            "name": "action_time",
            "type": "timestamp with time zone",
            "value": "2024-04-13 17:08:52.910565+00"
        },
        {
            "name": "object_id",
            "type": "text",
            "value": "1"
        },
        {
            "name": "object_repr",
            "type": "character varying(200)",
            "value": "admin"
        },
        {
            "name": "action_flag",
            "type": "smallint",
            "value": 2
        },
        {
            "name": "change_message",
            "type": "text",
            "value": "[]"
        },
        {
            "name": "content_type_id",
            "type": "integer",
            "value": 4
        },
        {
            "name": "user_id",
            "type": "integer",
            "value": 1
        }
    ],
    "schema": "public",
    "table": "django_admin_log"
}
```
