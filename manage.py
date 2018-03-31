#!/usr/bin/env python
import os
from app import create_app, db
from app.models import (
    CsvBodyCell,
    CsvBodyRow,
    CsvContainer,
    CsvHeaderCell,
    CsvHeaderRow,
    Resource,
    Role,
    User,
    RequiredOptionDescriptor,
)
from redis import Redis
from rq import Worker, Queue, Connection
from config import Config
from flask.ext.script import Manager, Shell
from flask.ext.migrate import Migrate, MigrateCommand

# Import settings from .env file. Must define FLASK_CONFIG
if os.path.exists('.env'):
    print('Importing environment from .env file')
    for line in open('.env'):
        var = line.strip().split('=')
        if len(var) == 2:
            os.environ[var[0]] = var[1]

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, User=User, Role=Role, CsvBodyCell=CsvBodyCell,
                CsvBodyRow=CsvBodyRow, CsvContainer=CsvContainer,
                CsvHeaderCell=CsvHeaderCell, CsvHeaderRow=CsvHeaderRow)


manager.add_command('shell', Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)


@manager.command
def test():
    """Run the unit tests."""
    import unittest

    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


@manager.command
def recreate_db():
    """
    Recreates a local database. You probably should not use this on
    production.
    """
    db.drop_all()
    db.create_all()
    db.session.commit()


@manager.option('-n',
                '--number-users',
                default=10,
                type=int,
                help='Number of each model type to create',
                dest='number_users')
def add_fake_data(number_users):
    """
    Adds fake data to the database.
    """
    User.generate_fake(count=number_users)
    Resource.generate_fake()


@manager.command
def setup_dev():
    """Runs the set-up needed for local development."""
    setup_general()

    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    if User.query.filter_by(email=admin_email).first() is None:
        User.create_confirmed_admin('Default',
                                    'Admin',
                                    admin_email,
                                    admin_password)


@manager.command
def setup_prod():
    """Runs the set-up needed for production."""
    setup_general()


def setup_general():
    """Runs the set-up needed for both local development and production."""
    Role.insert_roles()
    RequiredOptionDescriptor.init_required_option_descriptor()


@manager.command
def run_worker():
    """Initializes a slim rq task queue."""
    listen = ['default']
    conn = Redis(
        host=app.config['RQ_DEFAULT_HOST'],
        port=app.config['RQ_DEFAULT_PORT'],
        db=0,
        password=app.config['RQ_DEFAULT_PASSWORD']
    )

    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()


@manager.command
def migrate() :
    """Checks if a release on github requires a DB migration, 
        performs the migration. If no errors arise, the updated
        code is deployed to the heroku app"""

    """If you perform a database migration, you should always use transactions. 
    A transaction ensures that all migration operations are successful before 
    committing changes to the database... We suggest using heroku run, rather than release phase, 
    to correct your schema/data??"""

    """Your database migration script should check whether a database has already been migrated, 
    before executing a new migration (e.g., does table/column exist, if not add it).??"""

    """Grab an advisory lock. Many popular relational databases, such as Postgres and MySQL, 
    offer advisory lock functionality, which can be used to prevent concurrent migrations. """

    print("in migrate before")
    admin_email = "pearlmanhana@gmail.com"
    admin_password = "password"
    if User.query.filter_by(email=admin_email).first() is None:
        User.create_confirmed_admin('Hana',
                                    'Pearlman',
                                    admin_email,
                                    admin_password)
    print("in migrate after")


if __name__ == '__main__':
    manager.run()
