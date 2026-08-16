from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from src.database.db_setup import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="analyst")  # 'admin' | 'analyst'
    created_at = Column(DateTime, default=datetime.utcnow)

class CompanyAudit(Base):
    __tablename__ = "company_audits"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    avs_score = Column(Float, nullable=False)
    z_score = Column(Float, nullable=True)
    sloan_ratio = Column(Float, nullable=True)
    m_score = Column(Float, nullable=True)
    audit_date = Column(DateTime, default=datetime.utcnow)
    details_json = Column(Text, nullable=True)  # Store complete raw forensics

class AstroScanCache(Base):
    __tablename__ = "astro_scan_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, index=True, nullable=False)
    lagna = Column(String, nullable=True)
    moon_nakshatra = Column(String, nullable=True)
    mahadasha = Column(String, nullable=True)
    bhukti = Column(String, nullable=True)
    astro_growth_score = Column(Float, nullable=True)
    financial_quality_score = Column(Float, nullable=True)
    unified_alpha_score = Column(Float, nullable=True)
    interpreted_call = Column(String, nullable=True)
    last_cached = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
