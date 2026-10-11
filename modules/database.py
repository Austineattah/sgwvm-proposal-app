import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from config import Config

engine = create_engine(Config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class ConceptNote(Base):
    __tablename__ = "concept_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    org_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=False)
    ai_summary = Column(Text, nullable=True)
    payment_status = Column(String(50), default="UNPAID")
    review_status = Column(String(50), default="PENDING_REVIEW")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def save_concept_note(org_name: str, email: str, title: str, file_name: str, ai_summary: str, payment_status: str = "EXEMPT_OR_PENDING") -> int:
    init_db()
    session = SessionLocal()
    try:
        note = ConceptNote(
            org_name=org_name,
            email=email,
            title=title,
            file_name=file_name,
            ai_summary=ai_summary,
            payment_status=payment_status,
            review_status="PENDING_REVIEW"
        )
        session.add(note)
        session.commit()
        session.refresh(note)
        return note.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def fetch_all_concept_notes() -> list[dict]:
    init_db()
    session = SessionLocal()
    try:
        notes = session.query(ConceptNote).order_by(ConceptNote.created_at.desc()).all()
        return [
            {
                "id": n.id,
                "org_name": n.org_name,
                "email": n.email,
                "title": n.title,
                "file_name": n.file_name,
                "ai_summary": n.ai_summary,
                "payment_status": n.payment_status,
                "review_status": n.review_status,
                "created_at": n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else ""
            }
            for n in notes
        ]
    finally:
        session.close()

def update_concept_note_status(note_id: int, new_status: str) -> bool:
    init_db()
    session = SessionLocal()
    try:
        note = session.query(ConceptNote).filter(ConceptNote.id == note_id).first()
        if note:
            note.review_status = new_status
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        return False
    finally:
        session.close()
