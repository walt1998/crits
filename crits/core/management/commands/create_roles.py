from django.conf import settings
from django.core.management.base import BaseCommand
from optparse import make_option

import sys

from crits.core.role import Role

class Command(BaseCommand):
    """
    Script Class.
    """
    option_list = BaseCommand.option_list + (
        make_option("-a", "--all", action="store_true", dest="mall",
                    default=False,
                    help="Create All Roles and migrate legacy roles."),
        make_option("-A", "--Analyst", action="store_true",
                    dest="analyst",
                    default=False,
                    help="Create Analyst Role."),
        make_option("-m", "--migrate", action="store_true",
                    dest="migrate",
                    default=False,
                    help="Migrate legacy role to new Role"),
        make_option("-r", "--readonly", action="store_true",
                    dest="readonly",
                    default=False,
                    help="Create Rea Only Role."),
        make_option("-u", "--UberAdmin", action="store_true",
                    dest="uberadmin",
                    default=False,
                    help="Create UberAdmin Role."),
        )

    help = 'Creates the default UberAdmin Role in MongoDB.'

    def handle(self, *args, **options):
        """
        Script Execution.
        """
        mall = options.get('mall')
        analyst = options.get('analyst')
        migrate = options.get('migrate')
        readonly = options.get('readonly')
        uberadmin = options.get('uberadmin')


        if mall or uberadmin:
            add_uber_admin_role(True)
        if mall or readonly:
            add_readonly_role()
        if mall or analyst:
            add_analyst_role()
        if mall or migrate:
            migrate_roles()

        else:
            print("You must select something. See '-h' for options.")


def add_uber_admin_role(drop=False):
    """
    Add UberAdmin role to the system. This will always reset the UberAdmin role
    back to the original state if found in the database. If drop is set to True,
    all Roles will be removed and the default UberAdmin role will be added.

    The 'UberAdmin' role gets full access to *ALL* sources at the time it is
    created.

    If you wish to change the name of this role, you can change the ADMIN_ROLE
    settings variable.

    :param drop: Drop collection before adding.
    :type drop: boolean
    """

    if drop:
        print "Drop protection disabled. Dropping all Roles!"
        Role.drop_collection()
    else:
        print "Drop protection enabled!\nResetting 'UberAdmin' Role to defaults!"
    role = Role.objects(name=settings.ADMIN_ROLE).first()
    if not role:
        print "Could not find UberAdmin Role. Creating it!"
        role = Role()
        role.name = settings.ADMIN_ROLE
        role.description = "Default role with full system access."
    role.add_all_sources()
    role.make_all_true()
    role.save()

def add_readonly_role():
    """
    Add Read Only role to the system. This will always reset the Read Only role
    back to the original state if found in the database.

    """
    role = Role.objects(name='Read Only').first()
    if not role:
        role = Role()
        role.name = "Read Only"
        role.description = "Read Only Role"

    dont_modify = ['name',
                   'schema_version',
                   'active',
                   'id',
                   'description',
                   'unsupported_attrs']

    for p in role._data.iterkeys():
        if p in settings.CRITS_TYPES.iterkeys():
            attr = getattr(role, p)
            # Modify the attributes.
            for x in attr._data.iterkeys():
                if 'read' in str(x):
                    setattr(attr, x, True)
                else:
                    setattr(attr, x, False)
            # Set the attribute on the ACL.
            setattr(role, p, attr)
        elif p == "sources":
            for s in getattr(role, p):
                for x in s._data.iterkeys():
                    if x != "name":
                        setattr(s, x, True)

        elif p not in dont_modify:
            if p == 'api_interface' or p == 'web_interface' or p == 'script_interface':
                setattr(role, p, True)
            else:
                setattr(role, p, False)

    role.save()

def add_analyst_role():
    """
    Add Analyst role to the system. This will always reset the Analyst role
    back to the original state if found in the database.


    """
    role = Role.objects(name='Analyst').first()
    if not role:
        role = Role()
        role.name = "Analyst"
        role.description = "Default Analyst Role"

    dont_modify = ['name',
                   'schema_version',
                   'active',
                   'id',
                   'description',
                   'unsupported_attrs']

    for p in role._data.iterkeys():
        if p in settings.CRITS_TYPES.iterkeys():
            attr = getattr(role, p)
            # Modify the attributes.
            for x in attr._data.iterkeys():
                if 'delete' not in str(x):
                    setattr(attr, x, True)
                else:
                    setattr(attr, x, False)
            # Set the attribute on the ACL.
            setattr(role, p, attr)
        elif p == "sources":
            for s in getattr(role, p):
                for x in s._data.iterkeys():
                    if x != "name":
                        setattr(s, x, True)

        elif p not in dont_modify:
            if p == 'api_interface' or p == 'web_interface' or p == 'script_interface':
                setattr(role, p, True)
            else:
                setattr(role, p, False)

    role.save()

def migrate_roles():
    """
    Migrate legacy role objects to new RBAC Role objects

    """
    from pymongo import MongoClient

    c = MongoClient(settings.MONGO_HOST, settings.MONGO_PORT, ssl=settings.MONGO_SSL)
    db = c[settings.MONGO_DATABASE]
    if settings.MONGO_USER:
        db.authenticate(settings.MONGO_USER, settings.MONGO_PASSWORD)
    coll = db[settings.COL_USERS].find()

    for user in coll:
        try:
            role = user['role']
        except:
            role = user['unsupported_attrs']['role']

        try:
            roles = user['roles']
        except:
            roles = []
            
        if role == 'Administrator':
            roles.append('UberAdmin')
        elif role:
            roles.append(role)


        result = db.users.update_one(
           {"_id": user['_id']},
           {"$set": {"roles": roles}}
        )
