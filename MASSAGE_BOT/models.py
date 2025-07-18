from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class MassageType(Base):
    __tablename__ = 'massage_types'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)  # в минутах
    price = Column(Float, nullable=False)
    description = Column(Text)
    video = Column(String)  # путь к видео или ссылка
    image = Column(String)  # file_id Telegram или url картинки <--- ДОБАВЛЕНО!
    bookings = relationship('Booking', back_populates='massage_type')

class TimeSlot(Base):
    __tablename__ = 'time_slots'
    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_free = Column(Boolean, default=True)
    bookings = relationship('Booking', back_populates='slot')

class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    user_name = Column(String)
    massage_type_id = Column(Integer, ForeignKey('massage_types.id'))
    slot_id = Column(Integer, ForeignKey('time_slots.id'))
    massage_type = relationship('MassageType', back_populates='bookings')
    slot = relationship('TimeSlot', back_populates='bookings')
