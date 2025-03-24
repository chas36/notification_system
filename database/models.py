from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class Student(Base):
    __tablename__ = 'students'
    
    id = Column(Integer, primary_key=True)
    full_name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    
    notifications = relationship("Notification", back_populates="student")
    
    def __repr__(self):
        return f"<Student(full_name='{self.full_name}', class_name='{self.class_name}')>"

class Subject(Base):
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    
    def __repr__(self):
        return f"<Subject(name='{self.name}')>"

class TemplateType(Base):
    __tablename__ = 'template_types'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    file_path = Column(String, nullable=False)  # Путь к шаблону документа
    
    notifications = relationship("Notification", back_populates="template_type")
    
    def __repr__(self):
        return f"<TemplateType(name='{self.name}')>"

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    template_type_id = Column(Integer, ForeignKey('template_types.id'), nullable=False)
    period = Column(String, nullable=False)  # Модуль или триместр
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    student = relationship("Student", back_populates="notifications")
    template_type = relationship("TemplateType", back_populates="notifications")
    subjects = relationship("NotificationSubject", back_populates="notification")
    deadlines = relationship("DeadlineDate", back_populates="notification")
    
    def __repr__(self):
        return f"<Notification(student_id={self.student_id}, period='{self.period}')>"

class NotificationSubject(Base):
    __tablename__ = 'notification_subjects'
    
    id = Column(Integer, primary_key=True)
    notification_id = Column(Integer, ForeignKey('notifications.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    
    notification = relationship("Notification", back_populates="subjects")
    subject = relationship("Subject")
    
    def __repr__(self):
        return f"<NotificationSubject(notification_id={self.notification_id}, subject_id={self.subject_id})>"

class DeadlineDate(Base):
    __tablename__ = 'deadline_dates'
    
    id = Column(Integer, primary_key=True)
    notification_id = Column(Integer, ForeignKey('notifications.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    date = Column(String, nullable=False)
    time = Column(String)
    topic = Column(String)
    
    notification = relationship("Notification", back_populates="deadlines")
    subject = relationship("Subject")
    
    def __repr__(self):
        return f"<DeadlineDate(notification_id={self.notification_id}, subject_id={self.subject_id}, date='{self.date}')>"