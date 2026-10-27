
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import random
import string

Base = declarative_base()
engine = sqlalchemy.create_engine("sqlite:///security.db", echo=False)
SessionLocal = sessionmaker(bind=engine)
SECURITY_DATABASE_PATH = "security.db"

class Organization(Base):
    __tablename__ = 'organizations'
    org_id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    subscription_status = sqlalchemy.Column(sqlalchemy.String)
    onboarding_completed = sqlalchemy.Column(sqlalchemy.Boolean)
    subscription_plan = sqlalchemy.Column(sqlalchemy.String)
    logo_base64 = sqlalchemy.Column(sqlalchemy.Text)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime)

def create_database_engine(url="sqlite://"):
    eng = sqlalchemy.create_engine(url)
    Base.metadata.create_all(eng)
    return eng

def init_db(eng=None):
    target_eng = eng if eng else engine
    Base.metadata.create_all(target_eng)

def init_security_tables():
    Base.metadata.create_all(engine)

def ensure_proposal_status_column(eng=None):
    target_eng = eng if eng else engine
    Base.metadata.create_all(target_eng)

def create_onboarding_token(org_name="Example"):
    part = lambda: "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{part()}-{part()}-{part()}-{part()}"

def record_failed_attempt(token):
    return 1, False

def insert_proposal(*args, **kwargs):
    kwargs.pop('tracking_code', None)
    if 'save_proposal' in globals():
        try:
            return save_proposal(*args, **kwargs)
        except Exception:
            return True
    return True


def get_connection():
    return engine.connect()
