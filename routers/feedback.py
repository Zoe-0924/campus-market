from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
import models, database

router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.post("/")
def submit_feedback(
    name: str = Form(...), email: str = Form(...), message: str = Form(...),
    db: Session = Depends(database.get_db)
):
    db_feedback = models.Feedback(name=name, email=email, message=message)
    db.add(db_feedback)
    db.commit()
    return {"message": "回饋已成功送出，感謝您的建議！"}