import datetime
import os

from flask import Flask
from flask import jsonify
from flask import g
from flask import abort, render_template

from peewee import (Model, FixedCharField, CharField, ForeignKeyField,
                    fn, JOIN, DateTimeField, IntegerField, FixedCharField,
                    CompositeKey, FloatField)
from playhouse.db_url import connect


DATABASE_URL = os.environ['DATABASE_URL']
SECRET_KEY = os.environ['SECRET_KEY']
PROBE_URL = os.environ['PROBE_URL']
API_KEY = os.environ['API_KEY']
DEBUG = os.environ.get('DEBUG')


if DEBUG:
    import logging
    logger = logging.getLogger('peewee')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


app_start = datetime.datetime.utcnow()
dbconn = connect(DATABASE_URL)

app = Flask(__name__)
app.config.from_object(__name__)


class BaseModel(Model):
    class Meta:
        database = dbconn


class User(BaseModel):
    username = CharField()
    added = DateTimeField(default=datetime.datetime.utcnow)
    displayname = CharField(null=True)
    g = FixedCharField(null=True)

    @classmethod
    def get_existing_ids(cls, usernames):
        return cls.select(cls.id, cls.username).where(cls.username.in_(usernames)).namedtuples()

    @classmethod
    def get_all_ids(cls, names):
        existing_pairs = dict(cls.get_existing_ids(names))
        new_names = set(names) - set(existing_pairs.values())
        new_pairs = dict(cls.batch_add_users(new_names))
        existing_pairs.update(new_pairs)
        return existing_pairs

    @classmethod
    def batch_add_users(cls, usernames):
        cls.insert_many([{'username': name} for name in usernames]).execute()
        return cls.get_existing_ids(usernames)


class Sample(BaseModel):
    taken = DateTimeField()
    elapsed = FloatField()
    status = FixedCharField()


class PresencePoint(BaseModel):
    sample = ForeignKeyField(Sample, backref='sample')
    user = ForeignKeyField(User, backref='user')
    status = FixedCharField()

    class Meta:
        primary_key = CompositeKey('sample', 'user')


def save_sample(chunks):
    status = sample_status([chunk.status for chunk in chunks])
    with db.atomic():
        pass


def sample_status(chunk_status_list):
    st_set = set(chunk_status_list)
    if('success' in st_set):
        return 's' if len(st.set) == 1 else 'w'
    return 'w' if 'warning' in st_set else 'e'

@app.before_request
def before_request():
    g.db = dbconn
    g.db.connect()


@app.after_request
def after_request(response):
    g.db.close()
    return response


def get_object_or_error(model, *expressions, http_code=404):
    try:
        return model.get(*expressions)
    except model.DoesNotExist:
        abort(http_code)


@app.template_filter('uts_datetime')
def _jinja2_filter_uts_datetime(ts, fmt=None):
    utcdt = datetime.datetime.utcfromtimestamp(ts)
    return utcdt.strftime(fmt or '%Y-%m-%d %H:%M:%S')


@app.route('/')
def home():
    ctx = {
        'uptime': datetime.datetime.utcnow() - app_start
    }
    return render_template('home.html', **ctx)


@app.route('/putsample/<apikey>')
def put_sample(apikey):
    if apikey != API_KEY:
        abort(403)

    ts = datetime.datetime.utcnow()

    sample_id = Sample.put(apikey, ts)

    if insert_id:
        return jsonify(ts=ts, id=insert_id, status='ok'), 201
    else:
        return jsonify(status='error'), 400


def create_tables():
    with dbconn:
        dbconn.create_tables([User, Sample, PresencePoint])


def drop_tables():
    with dbconn:
        dbconn.drop_tables([User, Sample, PresencePoint])


if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=8080)
